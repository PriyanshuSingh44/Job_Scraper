from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./jobs.db"
    ingest_interval_minutes: int = 30
    max_failures_before_fallback: int = 3
    log_level: str = "INFO"

    # Scraping & Source Settings
    scrape_jitter_seconds: float = 1.5
    primary_source_url: str = "https://weworkremotely.com/categories/remote-full-stack-programming-jobs"
    fallback_rss_url: str = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
