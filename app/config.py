"""Typed application settings, optimized for AWS production and GitHub Actions CI."""

from functools import lru_cache
from typing import Any, Union
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    app_name: str = "NexaPilot AI"
    environment: str = "development"
    api_key: str = "change-me-dev-key"
    log_level: str = "INFO"
    cors_origins: Union[str, list[str]] = ["http://localhost:3000"]

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

    @property
    def is_test(self) -> bool:
        return self.environment.lower() in ("test", "ci")

    @model_validator(mode="before")
    @classmethod
    def parse_cors_origins(cls, values: dict[str, Any]) -> dict[str, Any]:
        cors = values.get("cors_origins")
        if isinstance(cors, str):
            values["cors_origins"] = [origin.strip() for origin in cors.split(",")]
        return values

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Fails fast on dangerous default values in production, ignoring test/CI runs."""
        if self.is_production and not self.is_test:
            if self.api_key == "change-me-dev-key":
                raise ValueError("API_KEY must be changed from default value in production!")
            if self.n8n_webhook_secret == "change-me-webhook-secret":
                raise ValueError("N8N_WEBHOOK_SECRET must be changed from default value in production!")
            if "db:5432" in self.database_url:
                raise ValueError("DATABASE_URL cannot point to local docker host ('db:5432') in production!")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
