"""Shared fixtures for fast, database-free M1 tests."""
import pytest
from fastapi.testclient import TestClient

from content_pilot.app import create_app
from content_pilot.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_name="ContentPilot Test", app_env="test", app_debug=False,
        postgres_host="localhost", postgres_port=5432, postgres_db="content_pilot_test",
        postgres_user="content_pilot_test", postgres_password="test-password",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
