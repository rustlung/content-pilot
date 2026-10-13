"""M3 workflow transitions use SQLite only; no publisher or network call is involved."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from content_pilot.db.base import Base
import content_pilot.models  # noqa: F401
from content_pilot.models.content_item import ContentItem
from content_pilot.models.enums import Platform, PostStatus
from content_pilot.models.post import Post
from content_pilot.models.project import Project
from content_pilot.services.errors import ConflictError, ValidationDomainError
from content_pilot.services.post_workflow import approve_post, cancel_post, schedule_post, unschedule_post


@pytest.fixture
def post(session: Session) -> Post:
    project = Project(name="Workflow project")
    item = ContentItem(project=project, title="Workflow item", content_type="educational")
    post = Post(content_item=item, platform=Platform.VK, text="Черновик для проверки workflow.")
    session.add(post)
    session.commit()
    return post


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(engine)() as session:
        yield session


def future_samara_time() -> datetime:
    return datetime.now(ZoneInfo("Europe/Samara")) + timedelta(days=1)


def test_approve_schedule_unschedule_and_cancel(session: Session, post: Post) -> None:
    assert approve_post(session, post.id).status is PostStatus.APPROVED
    local_time = future_samara_time()
    scheduled = schedule_post(session, post.id, local_time)
    assert scheduled.status is PostStatus.SCHEDULED
    assert scheduled.scheduled_at is not None
    # SQLite strips tzinfo, but the service must already have converted Samara input to UTC.
    assert scheduled.scheduled_at == local_time.astimezone(timezone.utc).replace(tzinfo=None)
    assert unschedule_post(session, post.id).status is PostStatus.APPROVED
    assert session.get(Post, post.id).scheduled_at is None
    assert cancel_post(session, post.id).status is PostStatus.CANCELLED


def test_draft_can_be_cancelled(session: Session, post: Post) -> None:
    assert cancel_post(session, post.id).status is PostStatus.CANCELLED


def test_linkedin_auto_schedule_is_rejected(session: Session) -> None:
    project = Project(name="Manual LinkedIn project")
    item = ContentItem(project=project, title="Manual item", content_type="educational")
    post = Post(content_item=item, platform=Platform.LINKEDIN, text="Текст для ручной публикации.")
    session.add(post)
    session.commit()

    approve_post(session, post.id)
    with pytest.raises(ConflictError, match="LinkedIn"):
        schedule_post(session, post.id, future_samara_time())


def test_invalid_transitions_and_past_schedule_fail(session: Session, post: Post) -> None:
    with pytest.raises(ConflictError):
        schedule_post(session, post.id, future_samara_time())
    approve_post(session, post.id)
    with pytest.raises(ValidationDomainError):
        schedule_post(session, post.id, datetime.now(timezone.utc) - timedelta(minutes=1))
    schedule_post(session, post.id, future_samara_time())
    post.status = PostStatus.PUBLISHED
    session.commit()
    with pytest.raises(ConflictError):
        approve_post(session, post.id)
    post.status = PostStatus.CANCELLED
    session.commit()
    with pytest.raises(ConflictError):
        schedule_post(session, post.id, future_samara_time())
