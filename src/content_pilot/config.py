"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class CeleryBootstrapSettings(BaseSettings):
    """Minimal import-safe configuration needed to construct the Celery app.

    Worker and Beat import this configuration before task execution, so it must
    not require database, AI, or social-provider credentials. Those settings
    remain validated by :class:`Settings` when a task opens application runtime
    resources.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    redis_host: str = "content-pilot-redis"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0)
    celery_broker_url: str | None = None
    celery_dispatch_interval_seconds: int = Field(default=60, ge=10)

    @cached_property
    def resolved_broker_url(self) -> str:
        return self.celery_broker_url or f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class PublicationSettings(BaseSettings):
    """Configuration required by Celery publication tasks and publishers only.

    This deliberately excludes database configuration. The worker gets its
    database session through the session factory, while publisher credentials
    and retry policy come directly from the runtime environment.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    publication_max_retries: int = Field(default=3, ge=0)
    publication_retry_base_seconds: int = Field(default=30, ge=1)
    publishing_dry_run: bool = False
    social_http_timeout_seconds: int = Field(default=30, ge=1, le=300)
    media_root: Path = Path("data/media")

    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    vk_access_token: SecretStr | None = None
    vk_group_id: str | None = None
    vk_api_version: str = "5.199"

    @field_validator("vk_api_version", mode="before")
    @classmethod
    def default_vk_api_version(cls, value: str | None) -> str:
        return value or "5.199"

    @field_validator("telegram_bot_token", "vk_access_token", mode="before")
    @classmethod
    def empty_secret_is_missing(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("telegram_chat_id", "vk_group_id", mode="before")
    @classmethod
    def empty_identifier_is_missing(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class AISettings(BaseSettings):
    """Configuration required by ProxyAPI-backed AI operations only."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    proxyapi_api_key: SecretStr | None = None
    proxyapi_base_url: str = "https://api.proxyapi.ru/v1"
    ai_text_model: str = "openai/gpt-4.1-mini"
    ai_image_model: str = "openai/gpt-image-1-mini"
    ai_timeout_seconds: int = Field(default=60, ge=1, le=300)

    @field_validator("proxyapi_api_key", mode="before")
    @classmethod
    def empty_secret_is_missing(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class Settings(BaseSettings):
    """Runtime settings. Secrets are never included in application logs."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ContentPilot"
    app_env: str = "development"
    app_debug: bool = True
    app_timezone: str = "Europe/Samara"

    postgres_host: str = "content-pilot-db"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "content_pilot"
    postgres_user: str = "content_pilot"
    postgres_password: SecretStr
    database_url: str | None = None

    redis_host: str = "content-pilot-redis"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0)
    celery_broker_url: str | None = None
    celery_dispatch_interval_seconds: int = Field(default=60, ge=10)
    celery_worker_concurrency: int = Field(default=1, ge=1)
    publication_max_retries: int = Field(default=3, ge=0)
    publication_retry_base_seconds: int = Field(default=30, ge=1)
    publishing_dry_run: bool = False
    social_http_timeout_seconds: int = Field(default=30, ge=1, le=300)

    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    vk_access_token: SecretStr | None = None
    vk_group_id: str | None = None
    vk_api_version: str = "5.199"

    proxyapi_api_key: SecretStr | None = None
    proxyapi_base_url: str = "https://api.proxyapi.ru/v1"
    ai_text_model: str = "openai/gpt-4.1-mini"
    ai_image_model: str = "openai/gpt-image-1-mini"
    ai_timeout_seconds: int = Field(default=60, ge=1, le=300)
    media_root: Path = Path("data/media")

    @field_validator("app_timezone")
    @classmethod
    def validate_app_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("APP_TIMEZONE must be a valid IANA timezone") from error
        return value

    @field_validator("vk_api_version", mode="before")
    @classmethod
    def default_vk_api_version(cls, value: str | None) -> str:
        return value or "5.199"

    @field_validator("telegram_bot_token", "vk_access_token", mode="before")
    @classmethod
    def empty_secret_is_missing(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("telegram_chat_id", "vk_group_id", mode="before")
    @classmethod
    def empty_identifier_is_missing(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value

    @cached_property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @cached_property
    def resolved_celery_broker_url(self) -> str:
        return self.celery_broker_url or f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

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
