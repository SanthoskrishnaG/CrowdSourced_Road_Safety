import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev_secret_key_1234567890"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/road_safety"
    UPLOAD_DIRECTORY: str = "uploads"

    # Allow loading from .env file if it exists
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
