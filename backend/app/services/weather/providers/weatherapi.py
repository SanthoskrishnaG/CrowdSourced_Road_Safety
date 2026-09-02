import logging
from datetime import datetime, timezone
from typing import Optional, List
import httpx

from app.core.config import settings
from app.services.weather.base import BaseWeatherProvider
from app.services.weather.models import WeatherData, WeatherForecastData, WeatherCondition, DailyForecast
from app.services.weather.providers.mock import MockWeatherProvider

logger = logging.getLogger("road_safety.weather.weatherapi")


class WeatherAPIProvider(BaseWeatherProvider):
    """
    Live weather provider integrating WeatherAPI.com.
    Reads credentials from WEATHERAPI_KEY or WEATHER_API_KEY.
    Gracefully falls back to MockWeatherProvider if API key is not configured or network fails.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.WEATHERAPI_KEY or settings.WEATHER_API_KEY
        self._mock_fallback = MockWeatherProvider()

    @property
    def provider_name(self) -> str:
        return "weatherapi"

    @property
    def is_mock(self) -> bool:
        return not bool(self.api_key)

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        if not self.api_key:
            logger.info("WeatherAPI key not provided. Falling back to MockWeatherProvider.")
            return await self._mock_fallback.get_current_weather(latitude, longitude)

        url = "https://api.weatherapi.com/v1/current.json"
        params = {
            "key": self.api_key,
            "q": f"{latitude},{longitude}",
            "aqi": "no"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return await self._mock_fallback.get_current_weather(latitude, longitude)

                data = resp.json()
                current = data.get("current", {})
                temp = float(current.get("temp_c", 25.0))
                humidity = float(current.get("humidity", 50.0))
                precip_mm = float(current.get("precip_mm", 0.0))
                wind_kph = float(current.get("wind_kph", 10.0))

                cond_text = current.get("condition", {}).get("text", "Clear")
                cond_lower = cond_text.lower()

                condition = WeatherCondition.CLEAR
                alert = None
                is_severe = False

                if "thunder" in cond_lower:
                    condition = WeatherCondition.THUNDERSTORM
                    alert = "Thunderstorm Warning in Region"
                    is_severe = True
                elif "heavy rain" in cond_lower or "torrential" in cond_lower:
                    condition = WeatherCondition.HEAVY_RAIN
                    alert = "Heavy Rain Advisory"
                    is_severe = True
                elif "rain" in cond_lower or "drizzle" in cond_lower:
                    condition = WeatherCondition.RAIN
                elif "cloud" in cond_lower or "overcast" in cond_lower:
                    condition = WeatherCondition.CLOUDY
                elif "fog" in cond_lower or "mist" in cond_lower:
                    condition = WeatherCondition.FOG
                elif "snow" in cond_lower:
                    condition = WeatherCondition.SNOW

                return WeatherData(
                    latitude=latitude,
                    longitude=longitude,
                    temperature_celsius=round(temp, 1),
                    humidity_percent=round(humidity, 1),
                    rainfall_mm_per_hour=round(precip_mm, 1),
                    rainfall_24h_mm=round(precip_mm * 5.0, 1),
                    wind_speed_kmh=round(wind_kph, 1),
                    condition=condition,
                    condition_description=cond_text,
                    severe_weather_alert=alert,
                    is_severe=is_severe,
                    is_mock=False,
                    provider_name="weatherapi",
                    timestamp=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.warning(f"Failed to fetch live weather from WeatherAPI: {e}. Falling back to mock.")
            return await self._mock_fallback.get_current_weather(latitude, longitude)

    async def get_forecast(self, latitude: float, longitude: float, days: int = 5) -> WeatherForecastData:
        if not self.api_key:
            return await self._mock_fallback.get_forecast(latitude, longitude, days)

        url = "https://api.weatherapi.com/v1/forecast.json"
        params = {
            "key": self.api_key,
            "q": f"{latitude},{longitude}",
            "days": min(10, days),
            "aqi": "no",
            "alerts": "yes"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return await self._mock_fallback.get_forecast(latitude, longitude, days)

                data = resp.json()
                forecast_days = data.get("forecast", {}).get("forecastday", [])
                daily: List[DailyForecast] = []

                for fd in forecast_days:
                    day_info = fd.get("day", {})
                    d_date = fd.get("date", "")
                    min_temp = float(day_info.get("mintemp_c", 20.0))
                    max_temp = float(day_info.get("maxtemp_c", 30.0))
                    total_precip = float(day_info.get("totalprecip_mm", 0.0))
                    cond_text = day_info.get("condition", {}).get("text", "Clear")

                    cond_enum = WeatherCondition.CLEAR
                    c_lower = cond_text.lower()
                    if "thunder" in c_lower:
                        cond_enum = WeatherCondition.THUNDERSTORM
                    elif "rain" in c_lower:
                        cond_enum = WeatherCondition.RAIN
                    elif "cloud" in c_lower:
                        cond_enum = WeatherCondition.CLOUDY

                    daily.append(DailyForecast(
                        date=d_date,
                        temp_min_celsius=round(min_temp, 1),
                        temp_max_celsius=round(max_temp, 1),
                        rainfall_expected_mm=round(total_precip, 1),
                        condition=cond_enum,
                        condition_description=cond_text,
                        severe_weather_alert="Flood Advisory" if total_precip > 25.0 else None,
                        is_severe=total_precip > 25.0
                    ))

                return WeatherForecastData(
                    latitude=latitude,
                    longitude=longitude,
                    provider_name="weatherapi",
                    is_mock=False,
                    daily_forecasts=daily,
                    generated_at=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.warning(f"Error in WeatherAPI forecast: {e}. Using mock fallback.")
            return await self._mock_fallback.get_forecast(latitude, longitude, days)
