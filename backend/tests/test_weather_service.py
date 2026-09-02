import pytest
from datetime import datetime
from app.services.weather.models import WeatherData, WeatherCondition, WeatherForecastData
from app.services.weather.providers.mock import MockWeatherProvider
from app.services.weather.providers.openweather import OpenWeatherMapProvider
from app.services.weather.providers.weatherapi import WeatherAPIProvider
from app.services.weather.service import WeatherService


@pytest.mark.anyio
async def test_mock_weather_provider_current():
    provider = MockWeatherProvider()
    assert provider.provider_name == "mock"
    assert provider.is_mock is True

    weather = await provider.get_current_weather(latitude=12.9716, longitude=77.5946)
    assert isinstance(weather, WeatherData)
    assert weather.latitude == 12.9716
    assert weather.longitude == 77.5946
    assert 0.0 <= weather.temperature_celsius <= 60.0
    assert 0.0 <= weather.humidity_percent <= 100.0
    assert weather.rainfall_mm_per_hour >= 0.0
    assert weather.rainfall_24h_mm >= 0.0
    assert weather.is_mock is True
    assert weather.provider_name == "mock"
    assert weather.condition in WeatherCondition


@pytest.mark.anyio
async def test_mock_weather_provider_forecast():
    provider = MockWeatherProvider()
    forecast = await provider.get_forecast(latitude=12.9716, longitude=77.5946, days=5)

    assert isinstance(forecast, WeatherForecastData)
    assert len(forecast.daily_forecasts) == 5
    assert forecast.is_mock is True
    for df in forecast.daily_forecasts:
        assert df.temp_max_celsius >= df.temp_min_celsius
        assert df.rainfall_expected_mm >= 0.0
        assert df.condition in WeatherCondition


@pytest.mark.anyio
async def test_weather_service_dynamic_provider():
    custom_mock = MockWeatherProvider()
    service = WeatherService(provider=custom_mock)
    assert service.provider.provider_name == "mock"

    weather = await service.get_current_weather(13.0827, 80.2707)
    assert weather.latitude == 13.0827
    assert weather.is_mock is True


@pytest.mark.anyio
async def test_real_provider_graceful_fallback_without_api_key():
    # Without real API key, OpenWeatherMapProvider falls back gracefully to Mock
    owm = OpenWeatherMapProvider(api_key=None)
    assert owm.is_mock is True
    weather = await owm.get_current_weather(12.9716, 77.5946)
    assert weather.is_mock is True
    assert weather.temperature_celsius > 0.0

    # WeatherAPIProvider fallback
    wapi = WeatherAPIProvider(api_key=None)
    assert wapi.is_mock is True
    weather_wapi = await wapi.get_current_weather(12.9716, 77.5946)
    assert weather_wapi.is_mock is True


def test_weather_api_endpoints(client):
    # Test GET /api/v1/weather/current
    res = client.get("/api/v1/weather/current?lat=12.9716&lon=77.5946")
    assert res.status_code == 200
    data = res.json()
    assert "temperature_celsius" in data
    assert "humidity_percent" in data
    assert "rainfall_mm_per_hour" in data
    assert "condition" in data
    assert "is_mock" in data
    assert "provider_name" in data

    # Test GET /api/v1/weather/forecast
    res_fc = client.get("/api/v1/weather/forecast?lat=12.9716&lon=77.5946&days=7")
    assert res_fc.status_code == 200
    fc_data = res_fc.json()
    assert len(fc_data["daily_forecasts"]) == 7
    assert fc_data["is_mock"] is True
