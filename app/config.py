from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./jobs.db", env="DATABASE_URL")
    ingest_interval_minutes: int = Field(default=30, env="INGEST_INTERVAL_MINUTES")
    max_failures_before_fallback: int = Field(default=3, env="MAX_FAILURES_BEFORE_FALLBACK")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
