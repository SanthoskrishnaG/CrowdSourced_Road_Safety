import os
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Environment
    ENVIRONMENT: str = "development"  # development, testing, production
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Security Configuration
    # 64-character default cryptographic key for local dev
    SECRET_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database Configuration
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/road_safety"

    # Static Assets & File Storage
    UPLOAD_DIRECTORY: str = "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # CORS Configuration
    CORS_ORIGINS: List[str] = ["*"]

    # Rate Limiting Configuration
    RATE_LIMIT_PER_MINUTE: int = 120

    # Duplicate Detection Scoring Engine Parameters
    DUPLICATE_DISTANCE_THRESHOLD_METERS: float = 50.0
    DUPLICATE_SCORE_THRESHOLD: float = 0.65
    WEIGHT_LOCATION: float = 0.40
    WEIGHT_CATEGORY: float = 0.30
    WEIGHT_TIME: float = 0.15
    WEIGHT_IMAGE: float = 0.15

    # Email & Notification Service Configuration
    EMAIL_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "notifications@roadsafety.gov"
    SMTP_FROM_NAME: str = "Road Infrastructure Safety Platform"

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "testing", "production"]
        val = v.lower()
        if val not in valid_envs:
            return "development"
        return val

    # Allow loading from .env file if it exists
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
