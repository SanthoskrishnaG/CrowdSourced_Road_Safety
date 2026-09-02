from abc import ABC, abstractmethod
from app.services.weather.models import WeatherData, WeatherForecastData


class BaseWeatherProvider(ABC):
    """
    Abstract base class for pluggable weather data providers.
    Ensures the platform is decoupled from any single third-party provider.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier name of this provider."""
        pass

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """Returns True if the provider returns simulated/mock data."""
        pass

    @abstractmethod
    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        """Fetch current weather conditions for the specified geographic coordinate."""
        pass

    @abstractmethod
    async def get_forecast(self, latitude: float, longitude: float, days: int = 5) -> WeatherForecastData:
        """Fetch multi-day weather forecast for the specified geographic coordinate."""
        pass
