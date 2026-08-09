"""Typed application settings, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "NexaPilot AI"
    environment: str = "development"
    api_key: str = "change-me-dev-key"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+asyncpg://nexapilot:nexapilot@db:5432/nexapilot"

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""

    tavily_api_key: str = ""

    n8n_webhook_url: str = ""
    n8n_webhook_secret: str = "change-me-webhook-secret"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
