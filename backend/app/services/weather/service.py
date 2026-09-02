import logging
from typing import Optional, Dict

from app.core.config import settings
from app.services.weather.base import BaseWeatherProvider
from app.services.weather.models import WeatherData, WeatherForecastData, WeatherCondition, DailyForecast
from app.services.weather.providers.mock import MockWeatherProvider
from app.services.weather.providers.openweather import OpenWeatherMapProvider
from app.services.weather.providers.weatherapi import WeatherAPIProvider

logger = logging.getLogger("road_safety.weather.service")


class WeatherService:
    """
    Singleton service manager for weather intelligence.
    Dynamically delegates to the configured BaseWeatherProvider implementation
    (OpenWeatherMap, WeatherAPI, or MockWeatherProvider).
    """

    def __init__(self, provider: Optional[BaseWeatherProvider] = None):
        self._provider = provider or self._resolve_provider()

    def _resolve_provider(self) -> BaseWeatherProvider:
        provider_name = (settings.WEATHER_PROVIDER or "mock").lower()

        if provider_name == "openweather" or provider_name == "openweathermap":
            return OpenWeatherMapProvider()
        elif provider_name == "weatherapi":
            return WeatherAPIProvider()
        else:
            return MockWeatherProvider()

    @property
    def provider(self) -> BaseWeatherProvider:
        return self._provider

    def set_provider(self, provider: BaseWeatherProvider) -> None:
        """Allows runtime or test injection of custom weather providers."""
        self._provider = provider

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        return await self._provider.get_current_weather(latitude, longitude)

    async def get_forecast(self, latitude: float, longitude: float, days: int = 5) -> WeatherForecastData:
        return await self._provider.get_forecast(latitude, longitude, days)


# Global singleton instance
weather_service = WeatherService()
