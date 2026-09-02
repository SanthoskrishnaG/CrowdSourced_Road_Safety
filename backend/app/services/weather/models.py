import enum
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


class WeatherCondition(str, enum.Enum):
    CLEAR = "CLEAR"
    CLOUDY = "CLOUDY"
    RAIN = "RAIN"
    HEAVY_RAIN = "HEAVY_RAIN"
    THUNDERSTORM = "THUNDERSTORM"
    FOG = "FOG"
    SNOW = "SNOW"
    EXTREME = "EXTREME"


class WeatherData(BaseModel):
    latitude: float
    longitude: float
    temperature_celsius: float = Field(..., description="Current temperature in Celsius")
    humidity_percent: float = Field(..., ge=0.0, le=100.0, description="Relative humidity percentage")
    rainfall_mm_per_hour: float = Field(default=0.0, ge=0.0, description="Instantaneous precipitation rate (mm/h)")
    rainfall_24h_mm: float = Field(default=0.0, ge=0.0, description="Cumulative 24-hour precipitation (mm)")
    wind_speed_kmh: float = Field(default=0.0, ge=0.0, description="Wind speed in km/h")
    condition: WeatherCondition = Field(default=WeatherCondition.CLEAR)
    condition_description: str = Field(default="Clear Skies")
    severe_weather_alert: Optional[str] = Field(default=None, description="Active severe weather warning or advisory")
    is_severe: bool = Field(default=False)
    is_mock: bool = Field(default=False, description="True if simulated / development data, False if real provider API")
    provider_name: str = Field(default="mock", description="Identifier of the weather source provider")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DailyForecast(BaseModel):
    date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    temp_min_celsius: float
    temp_max_celsius: float
    rainfall_expected_mm: float
    condition: WeatherCondition
    condition_description: str
    severe_weather_alert: Optional[str] = None
    is_severe: bool = False


class WeatherForecastData(BaseModel):
    latitude: float
    longitude: float
    provider_name: str
    is_mock: bool
    daily_forecasts: List[DailyForecast] = []
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
