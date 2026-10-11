"""Shared fixtures for fast, database-free M1 tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from content_pilot.app import create_app
from content_pilot.config import Settings
from content_pilot.db.base import Base
from content_pilot.db.session import get_session
import content_pilot.models  # noqa: F401


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_name="ContentPilot Test", app_env="test", app_debug=False,
        postgres_host="localhost", postgres_port=5432, postgres_db="content_pilot_test",
        postgres_user="content_pilot_test", postgres_password="test-password",
    )


@pytest.fixture
def client(settings: Settings, tmp_path) -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session: Session = sessionmaker(engine)()
    app = create_app(settings.model_copy(update={"media_root": tmp_path}))
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    session.close()
