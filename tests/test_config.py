"""Settings validation and safe database URL construction."""
import pytest
from pydantic import ValidationError

from content_pilot.config import Settings


def test_settings_builds_database_url() -> None:
    settings = Settings(postgres_password="safe@password")
    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://content_pilot:")
    assert "safe%40password" in settings.sqlalchemy_database_url


def test_settings_requires_postgres_password() -> None:
    with pytest.raises(ValidationError):
        Settings(postgres_password=None)  # type: ignore[arg-type]


def test_settings_uses_valid_iana_timezone() -> None:
    assert str(Settings(postgres_password="test-password").timezone) == "Europe/Samara"
    with pytest.raises(ValidationError):
        Settings(postgres_password="test-password", app_timezone="not/a-timezone")


def test_settings_builds_default_celery_broker_url() -> None:
    settings = Settings(postgres_password="test-password")
    assert settings.resolved_celery_broker_url == "redis://content-pilot-redis:6379/0"
