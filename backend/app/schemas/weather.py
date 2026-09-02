import enum
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WeatherConditionEnum(str, enum.Enum):
    CLEAR = "CLEAR"
    CLOUDY = "CLOUDY"
    RAIN = "RAIN"
    HEAVY_RAIN = "HEAVY_RAIN"
    THUNDERSTORM = "THUNDERSTORM"
    FOG = "FOG"
    SNOW = "SNOW"
    EXTREME = "EXTREME"


class CurrentWeatherResponse(BaseModel):
    latitude: float
    longitude: float
    temperature_celsius: float
    humidity_percent: float
    rainfall_mm_per_hour: float
    rainfall_24h_mm: float
    wind_speed_kmh: float
    condition: WeatherConditionEnum
    condition_description: str
    severe_weather_alert: Optional[str] = None
    is_severe: bool = False
    is_mock: bool = Field(..., description="True if mock/simulated data; False if live provider")
    provider_name: str
    timestamp: datetime


class DailyForecastItem(BaseModel):
    date: str
    temp_min_celsius: float
    temp_max_celsius: float
    rainfall_expected_mm: float
    condition: WeatherConditionEnum
    condition_description: str
    severe_weather_alert: Optional[str] = None
    is_severe: bool = False


class WeatherForecastResponse(BaseModel):
    latitude: float
    longitude: float
    provider_name: str
    is_mock: bool
    daily_forecasts: List[DailyForecastItem]
    generated_at: datetime


class CategoryCorrelationMetric(BaseModel):
    category: str
    pearson_r: float = Field(..., description="Pearson correlation coefficient (-1.0 to 1.0)")
    spearman_r: float = Field(..., description="Spearman rank correlation coefficient (-1.0 to 1.0)")
    total_incidents: int
    rainy_day_incidents: int
    dry_day_incidents: int
    rainfall_multiplier: float = Field(..., description="Incidence rate ratio on rainy vs dry periods")
    significance: str = Field(..., description="HIGH, MODERATE, LOW, or NEGLIGIBLE")
    insight: str


class WeatherProblemTrendPoint(BaseModel):
    date: str
    daily_rainfall_mm: float
    flooding_reports: int
    pothole_reports: int
    road_damage_reports: int
    total_hazards: int


class WeatherCorrelationAnalyticsResponse(BaseModel):
    time_window_days: int
    data_provenance: str = Field(default="Hybrid Provider + Spatial Telemetry")
    is_mock_provider: bool
    summary: Dict[str, Any]
    category_correlations: List[CategoryCorrelationMetric]
    trend_history: List[WeatherProblemTrendPoint]
    advisory_recommendations: List[str]
