"""End-to-end M2 API flow against SQLite and a fake provider."""
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from content_pilot.api.dependencies import get_ai_provider
from content_pilot.app import create_app
from content_pilot.config import Settings
from content_pilot.db.base import Base
from content_pilot.db.session import get_session
import content_pilot.models  # noqa: F401
from tests.test_m2_services import FakeAI


def test_manual_generation_api_flow(tmp_path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    settings = Settings(postgres_password="test-password", media_root=tmp_path)
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_ai_provider] = lambda: FakeAI()
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "API проект"})
    assert project.status_code == 201
    assert project.json()["language"] == "ru"
    project_id = project.json()["id"]
    plan = client.post(
        f"/api/projects/{project_id}/content-plan/generate",
        json={"start_date": "2026-10-10", "end_date": "2026-10-20", "posts_count": 1, "platforms": ["linkedin"]},
    )
    assert plan.status_code == 200
    item_id = plan.json()[0]["id"]
    post = client.post(f"/api/content-items/{item_id}/posts/generate", json={"platform": "linkedin"})
    assert post.status_code == 200
    media = client.post(f"/api/posts/{post.json()['id']}/image/generate")
    assert media.status_code == 200
    assert media.json()["media_url"].endswith(media.json()["file_path"])
    assert client.get(f"/api/projects/{uuid4()}").status_code == 404
    bad_period = client.post(f"/api/projects/{project_id}/content-plan/generate", json={"start_date": "2026-10-20", "end_date": "2026-10-10", "posts_count": 1, "platforms": ["vk"]})
    assert bad_period.status_code == 422
    session.close()
