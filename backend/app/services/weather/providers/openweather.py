import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import httpx

from app.core.config import settings
from app.services.weather.base import BaseWeatherProvider
from app.services.weather.models import WeatherData, WeatherForecastData, WeatherCondition, DailyForecast
from app.services.weather.providers.mock import MockWeatherProvider

logger = logging.getLogger("road_safety.weather.openweather")


class OpenWeatherMapProvider(BaseWeatherProvider):
    """
    Live weather provider integrating OpenWeatherMap OneCall / Weather API.
    Reads credentials from OPENWEATHERMAP_API_KEY or WEATHER_API_KEY.
    Gracefully falls back to MockWeatherProvider if API key is not configured or network fails.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENWEATHERMAP_API_KEY or settings.WEATHER_API_KEY
        self._mock_fallback = MockWeatherProvider()

    @property
    def provider_name(self) -> str:
        return "openweathermap"

    @property
    def is_mock(self) -> bool:
        return not bool(self.api_key)

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        if not self.api_key:
            logger.info("OpenWeatherMap API key not provided. Falling back to MockWeatherProvider.")
            return await self._mock_fallback.get_current_weather(latitude, longitude)

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "metric"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"OpenWeatherMap returned status {resp.status_code}. Using mock fallback.")
                    return await self._mock_fallback.get_current_weather(latitude, longitude)

                data = resp.json()
                temp = float(data.get("main", {}).get("temp", 25.0))
                humidity = float(data.get("main", {}).get("humidity", 50.0))
                wind_speed_ms = float(data.get("wind", {}).get("speed", 3.0))
                wind_speed_kmh = round(wind_speed_ms * 3.6, 1)

                # Precipitation
                rain_1h = float(data.get("rain", {}).get("1h", 0.0))
                rain_3h = float(data.get("rain", {}).get("3h", 0.0))
                rain_24h = max(rain_1h * 6.0, rain_3h * 2.0)

                # Weather condition mapping
                weather_items = data.get("weather", [{}])
                main_condition = weather_items[0].get("main", "Clear").upper()
                desc = weather_items[0].get("description", "Clear").capitalize()

                condition = WeatherCondition.CLEAR
                alert = None
                is_severe = False

                if "THUNDER" in main_condition:
                    condition = WeatherCondition.THUNDERSTORM
                    alert = "Thunderstorm Warning in Region"
                    is_severe = True
                elif "RAIN" in main_condition or "DRIZZLE" in main_condition:
                    if rain_1h > 10.0:
                        condition = WeatherCondition.HEAVY_RAIN
                        alert = "Heavy Rain Advisory"
                        is_severe = True
                    else:
                        condition = WeatherCondition.RAIN
                elif "CLOUD" in main_condition:
                    condition = WeatherCondition.CLOUDY
                elif "FOG" in main_condition or "MIST" in main_condition or "HAZE" in main_condition:
                    condition = WeatherCondition.FOG
                elif "SNOW" in main_condition:
                    condition = WeatherCondition.SNOW

                return WeatherData(
                    latitude=latitude,
                    longitude=longitude,
                    temperature_celsius=round(temp, 1),
                    humidity_percent=round(humidity, 1),
                    rainfall_mm_per_hour=round(rain_1h, 1),
                    rainfall_24h_mm=round(rain_24h, 1),
                    wind_speed_kmh=wind_speed_kmh,
                    condition=condition,
                    condition_description=desc,
                    severe_weather_alert=alert,
                    is_severe=is_severe,
                    is_mock=False,
                    provider_name="openweathermap",
                    timestamp=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.warning(f"Failed to fetch live weather from OpenWeatherMap: {e}. Falling back to mock.")
            return await self._mock_fallback.get_current_weather(latitude, longitude)

    async def get_forecast(self, latitude: float, longitude: float, days: int = 5) -> WeatherForecastData:
        if not self.api_key:
            return await self._mock_fallback.get_forecast(latitude, longitude, days)

        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "metric",
            "cnt": min(40, days * 8)
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return await self._mock_fallback.get_forecast(latitude, longitude, days)

                data = resp.json()
                forecast_list = data.get("list", [])
                daily_map = {}

                for item in forecast_list:
                    dt_txt = item.get("dt_txt", "")
                    date_str = dt_txt.split(" ")[0] if " " in dt_txt else datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    temp = float(item.get("main", {}).get("temp", 25.0))
                    rain_3h = float(item.get("rain", {}).get("3h", 0.0))

                    if date_str not in daily_map:
                        daily_map[date_str] = {
                            "min_temp": temp,
                            "max_temp": temp,
                            "total_rain": rain_3h,
                            "condition": item.get("weather", [{}])[0].get("main", "Clear"),
                            "desc": item.get("weather", [{}])[0].get("description", "Clear").capitalize()
                        }
                    else:
                        daily_map[date_str]["min_temp"] = min(daily_map[date_str]["min_temp"], temp)
                        daily_map[date_str]["max_temp"] = max(daily_map[date_str]["max_temp"], temp)
                        daily_map[date_str]["total_rain"] += rain_3h

                daily: List[DailyForecast] = []
                for d_str, v in list(daily_map.items())[:days]:
                    cond_enum = WeatherCondition.CLEAR
                    c_upper = v["condition"].upper()
                    if "THUNDER" in c_upper:
                        cond_enum = WeatherCondition.THUNDERSTORM
                    elif "RAIN" in c_upper:
                        cond_enum = WeatherCondition.RAIN
                    elif "CLOUD" in c_upper:
                        cond_enum = WeatherCondition.CLOUDY

                    daily.append(DailyForecast(
                        date=d_str,
                        temp_min_celsius=round(v["min_temp"], 1),
                        temp_max_celsius=round(v["max_temp"], 1),
                        rainfall_expected_mm=round(v["total_rain"], 1),
                        condition=cond_enum,
                        condition_description=v["desc"],
                        severe_weather_alert="Heavy Rain Expected" if v["total_rain"] > 25.0 else None,
                        is_severe=v["total_rain"] > 25.0
                    ))

                return WeatherForecastData(
                    latitude=latitude,
                    longitude=longitude,
                    provider_name="openweathermap",
                    is_mock=False,
                    daily_forecasts=daily,
                    generated_at=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.warning(f"Error in OpenWeatherMap forecast: {e}. Using mock fallback.")
            return await self._mock_fallback.get_forecast(latitude, longitude, days)
