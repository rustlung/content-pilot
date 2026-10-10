"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import cached_property

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Runtime settings. Secrets are never included in application logs."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ContentPilot"
    app_env: str = "development"
    app_debug: bool = True

    postgres_host: str = "content-pilot-db"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "content_pilot"
    postgres_user: str = "content_pilot"
    postgres_password: SecretStr
    database_url: str | None = None

    redis_host: str = "content-pilot-redis"
    redis_port: int = Field(default=6379, ge=1, le=65535)

    @cached_property
    def sqlalchemy_database_url(self) -> str:
        """Return an explicit URL when set, otherwise build a safely escaped URL."""
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)
