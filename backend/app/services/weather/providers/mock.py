import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from app.services.weather.base import BaseWeatherProvider
from app.services.weather.models import WeatherData, WeatherForecastData, WeatherCondition, DailyForecast


class MockWeatherProvider(BaseWeatherProvider):
    """
    Mock/Simulated weather provider for local development, CI/CD, and offline testing.
    Produces deterministic, realistic weather variations without requiring any external network or API key.
    Explicitly flags all data with `is_mock = True`.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def is_mock(self) -> bool:
        return True

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        now = datetime.now(timezone.utc)
        day_of_year = now.timetuple().tm_yday
        hour = now.hour

        # Base temperature variation by latitude & time of day
        base_temp = 28.0 - (abs(latitude - 13.0) * 0.8) + (math.sin(hour / 24.0 * 2 * math.pi - math.pi / 2) * 5.0)
        temp_celsius = round(max(10.0, min(45.0, base_temp)), 1)

        # Humidity correlated with hour and coordinate seed
        coord_seed = (abs(latitude) * 100 + abs(longitude) * 10) % 50
        base_humidity = 65.0 + (math.cos(hour / 24.0 * 2 * math.pi) * 15.0) + (coord_seed * 0.2)
        humidity = round(max(30.0, min(98.0, base_humidity)), 1)

        # Rainfall simulation: seasonal periodic pattern with localized bursts
        rain_factor = (math.sin(day_of_year / 365.0 * 2 * math.pi) + math.sin(coord_seed)) / 2.0
        if rain_factor > 0.4:
            rain_rate = round((rain_factor - 0.4) * 25.0, 1)  # 0 to 15 mm/h
            rain_24h = round(rain_rate * 4.5 + 5.0, 1)
            if rain_rate > 15.0:
                condition = WeatherCondition.THUNDERSTORM
                desc = "Heavy Thunderstorms & Intense Downpour"
                alert = "Severe Thunderstorm & Flash Flood Advisory"
                is_severe = True
            elif rain_rate > 7.0:
                condition = WeatherCondition.HEAVY_RAIN
                desc = "Heavy Rainfall with Surface Water Accumulation"
                alert = "Heavy Rain Alert"
                is_severe = True
            else:
                condition = WeatherCondition.RAIN
                desc = "Moderate Rain Showers"
                alert = None
                is_severe = False
        elif humidity > 85.0:
            rain_rate = 0.0
            rain_24h = 0.0
            condition = WeatherCondition.CLOUDY
            desc = "Overcast Clouds"
            alert = None
            is_severe = False
        else:
            rain_rate = 0.0
            rain_24h = 0.0
            condition = WeatherCondition.CLEAR
            desc = "Clear Sunny Conditions"
            alert = None
            is_severe = False

        wind_speed = round(8.0 + (abs(math.sin(hour)) * 14.0), 1)

        return WeatherData(
            latitude=latitude,
            longitude=longitude,
            temperature_celsius=temp_celsius,
            humidity_percent=humidity,
            rainfall_mm_per_hour=rain_rate,
            rainfall_24h_mm=rain_24h,
            wind_speed_kmh=wind_speed,
            condition=condition,
            condition_description=desc,
            severe_weather_alert=alert,
            is_severe=is_severe,
            is_mock=True,
            provider_name="mock",
            timestamp=now
        )

    async def get_forecast(self, latitude: float, longitude: float, days: int = 5) -> WeatherForecastData:
        now = datetime.now(timezone.utc)
        daily: List[DailyForecast] = []

        for d in range(days):
            target_date = now + timedelta(days=d)
            date_str = target_date.strftime("%Y-%m-%d")
            seed = (abs(latitude) + abs(longitude) + d * 7) % 10

            min_temp = round(21.0 + (seed * 0.5), 1)
            max_temp = round(min_temp + 8.0 + (seed * 0.4), 1)

            if seed > 6:
                cond = WeatherCondition.RAIN
                desc = "Scattered Monsoonal Showers"
                rain_exp = round(12.0 + seed * 2.5, 1)
                alert = "Flood Watch" if rain_exp > 20.0 else None
                is_severe = rain_exp > 20.0
            elif seed > 4:
                cond = WeatherCondition.CLOUDY
                desc = "Partly Cloudy with Humid Breeze"
                rain_exp = round(2.0, 1)
                alert = None
                is_severe = False
            else:
                cond = WeatherCondition.CLEAR
                desc = "Clear Pavement & Dry Conditions"
                rain_exp = 0.0
                alert = None
                is_severe = False

            daily.append(DailyForecast(
                date=date_str,
                temp_min_celsius=min_temp,
                temp_max_celsius=max_temp,
                rainfall_expected_mm=rain_exp,
                condition=cond,
                condition_description=desc,
                severe_weather_alert=alert,
                is_severe=is_severe
            ))

        return WeatherForecastData(
            latitude=latitude,
            longitude=longitude,
            provider_name="mock",
            is_mock=True,
            daily_forecasts=daily,
            generated_at=now
        )
