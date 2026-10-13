"""M6 aggregate analytics stay local to SQLAlchemy and require no provider calls."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from content_pilot.app import create_app
from content_pilot.config import Settings
from content_pilot.db.base import Base
from content_pilot.db.session import get_session
from content_pilot.models.content_item import ContentItem
from content_pilot.models.enums import MediaSource, MediaType, Platform, PostStatus, PublicationAttemptStatus
from content_pilot.models.media_asset import MediaAsset
from content_pilot.models.post import Post
from content_pilot.models.project import Project
from content_pilot.models.publication_attempt import PublicationAttempt
from content_pilot.services.dashboard import dashboard_data, project_analytics
import content_pilot.models  # noqa: F401


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(engine)()


def test_dashboard_analytics_counts_platforms_and_attempt_metrics() -> None:
    session = make_session()
    project = Project(name="Analytics project")
    item = ContentItem(project=project, title="Published item", content_type="educational")
    published = Post(
        content_item=item,
        platform=Platform.TELEGRAM,
        text="Published",
        status=PostStatus.PUBLISHED,
        published_at=datetime.now(timezone.utc),
    )
    failed = Post(content_item=item, platform=Platform.VK, text="Failed", status=PostStatus.FAILED)
    draft = Post(content_item=item, platform=Platform.LINKEDIN, text="Draft", status=PostStatus.DRAFT)
    session.add_all([published, failed, draft])
    session.flush()
    session.add_all(
        [
            PublicationAttempt(post=published, attempt_no=1, status=PublicationAttemptStatus.FAILED),
            PublicationAttempt(post=published, attempt_no=2, status=PublicationAttemptStatus.SUCCESS),
            PublicationAttempt(post=failed, attempt_no=1, status=PublicationAttemptStatus.FAILED),
        ]
    )
    session.commit()

    data = dashboard_data(session)
    assert data["counts"]["published"] == 1
    assert data["counts"]["failed"] == 1
    assert data["platform_counts"] == {"linkedin": 1, "vk": 1, "telegram": 1}
    assert data["attempt_counts"] == {"success": 1, "failed": 2, "retries": 1, "avg_per_published": 2.0}
    assert [post.id for post in data["published"]] == [published.id]


def test_project_analytics_has_status_and_platform_breakdown() -> None:
    session = make_session()
    project = Project(name="Project metrics")
    item = ContentItem(project=project, title="Item", content_type="educational")
    session.add_all(
        [
            Post(content_item=item, platform=Platform.VK, status=PostStatus.SCHEDULED),
            Post(content_item=item, platform=Platform.TELEGRAM, status=PostStatus.PUBLISHED),
        ]
    )
    session.commit()

    analytics = project_analytics(session, project.id)
    assert analytics.content_items == 1
    assert analytics.posts == 2
    assert analytics.by_status["scheduled"] == 1
    assert analytics.by_status["published"] == 1
    assert analytics.by_platform["vk"] == 1
    assert analytics.by_platform["telegram"] == 1


def test_post_detail_renders_publication_history_and_vk_media_note(tmp_path) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    project = Project(name="History project")
    item = ContentItem(project=project, title="VK post", content_type="educational")
    post = Post(content_item=item, platform=Platform.VK, text="Published", status=PostStatus.PUBLISHED)
    session.add(post)
    session.flush()
    session.add(
        PublicationAttempt(
            post=post,
            attempt_no=1,
            status=PublicationAttemptStatus.SUCCESS,
            external_response_id="vk:wall-1_2",
        )
    )
    session.add(
        MediaAsset(
            post=post,
            media_type=MediaType.IMAGE,
            source=MediaSource.AI,
            file_path="example.png",
        )
    )
    session.commit()
    app = create_app(Settings(postgres_password="test-password", media_root=tmp_path))
    app.dependency_overrides[get_session] = lambda: session

    with TestClient(app) as client:
        response = client.get(f"/posts/{post.id}")
    assert response.status_code == 200
    assert "История публикации" in response.text
    assert "vk:wall-1_2" in response.text
    assert "Текст опубликован в VK" in response.text
    assert "доступно ниже для ручной публикации" in response.text
