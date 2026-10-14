"""M4 publication state persistence tests; no Redis or network is required."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from content_pilot.db.base import Base
from content_pilot.config import PublicationSettings
from content_pilot.models.content_item import ContentItem
from content_pilot.models.enums import Platform, PostStatus, PublicationAttemptStatus
from content_pilot.models.post import Post
from content_pilot.models.project import Project
from content_pilot.models.publication_attempt import PublicationAttempt
from content_pilot.services.publication import (
    claim_scheduled_post,
    finish_failure,
    finish_success,
    queue_failed_post_for_manual_retry,
    start_attempt,
    task_owns_publishing_post,
)
from content_pilot.services.errors import ConflictError
from content_pilot.tasks import publishing
from content_pilot.tasks import scheduling
import content_pilot.models  # noqa: F401


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(engine)()


def make_post(session: Session, *, status: PostStatus, scheduled_at: datetime | None) -> Post:
    project = Project(name="M4 project")
    item = ContentItem(project=project, title="M4 item", content_type="educational")
    post = Post(
        content_item=item,
        platform=Platform.VK,
        text="Тестовый текст.",
        status=status,
        scheduled_at=scheduled_at,
    )
    session.add(post)
    session.commit()
    return post


def test_atomic_due_claim_allows_only_one_worker() -> None:
    session = make_session()
    post = make_post(
        session,
        status=PostStatus.SCHEDULED,
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    assert claim_scheduled_post(session, post.id) is True
    assert claim_scheduled_post(session, post.id) is False
    assert session.get(Post, post.id).status is PostStatus.PUBLISHING


def test_claim_ignores_future_and_non_scheduled_posts() -> None:
    session = make_session()
    future = make_post(
        session,
        status=PostStatus.SCHEDULED,
        scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    approved = make_post(session, status=PostStatus.APPROVED, scheduled_at=None)

    assert claim_scheduled_post(session, future.id) is False
    assert claim_scheduled_post(session, approved.id) is False


def test_success_records_attempt_and_publishes_post() -> None:
    session = make_session()
    post = make_post(
        session,
        status=PostStatus.SCHEDULED,
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert claim_scheduled_post(session, post.id)
    attempt = start_attempt(session, post.id, "task-a")
    assert task_owns_publishing_post(session, post.id, "task-a")

    finish_success(session, post.id, attempt.id, "dry-run:post-1")

    stored = session.get(Post, post.id)
    stored_attempt = session.get(PublicationAttempt, attempt.id)
    assert stored.status is PostStatus.PUBLISHED
    assert stored.external_post_id == "dry-run:post-1"
    assert stored.published_at is not None
    assert stored.scheduled_at is not None
    assert stored_attempt.status is PublicationAttemptStatus.SUCCESS
    assert stored_attempt.external_response_id == "dry-run:post-1"


def test_retryable_attempt_keeps_post_publishing_and_other_task_cannot_own_it() -> None:
    session = make_session()
    post = make_post(
        session,
        status=PostStatus.SCHEDULED,
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert claim_scheduled_post(session, post.id)
    attempt = start_attempt(session, post.id, "task-a")
    finish_failure(session, post.id, attempt.id, "temporary outage", final=False)

    assert session.get(Post, post.id).status is PostStatus.PUBLISHING
    assert task_owns_publishing_post(session, post.id, "task-a")
    assert not task_owns_publishing_post(session, post.id, "task-b")
    assert session.scalar(select(PublicationAttempt.status).where(PublicationAttempt.id == attempt.id)) is PublicationAttemptStatus.FAILED


def test_final_failure_marks_post_failed() -> None:
    session = make_session()
    post = make_post(
        session,
        status=PostStatus.SCHEDULED,
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert claim_scheduled_post(session, post.id)
    attempt = start_attempt(session, post.id, "task-a")
    finish_failure(session, post.id, attempt.id, "publisher unavailable", final=True)

    stored = session.get(Post, post.id)
    assert stored.status is PostStatus.FAILED
    assert stored.last_error == "publisher unavailable"


def test_manual_retry_reuses_failed_post_and_continues_attempt_history(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        post = make_post(session, status=PostStatus.FAILED, scheduled_at=None)
        session.add(
            PublicationAttempt(
                post_id=post.id,
                attempt_no=1,
                status=PublicationAttemptStatus.FAILED,
                error="previous safe error",
            )
        )
        session.commit()
        post_id = str(post.id)
        queued = queue_failed_post_for_manual_retry(session, post.id)
        assert queued.status is PostStatus.SCHEDULED
        assert queued.last_error is None
        with pytest.raises(ConflictError):
            queue_failed_post_for_manual_retry(session, post.id)

    class FakePublisher:
        def publish(self, post: Post, media) -> publishing.PublicationResult:
            return publishing.PublicationResult("fake:manual-retry")

    monkeypatch.setattr(publishing, "get_session_factory", lambda: factory)
    monkeypatch.setattr(publishing, "get_publication_settings", lambda: PublicationSettings(_env_file=None))
    monkeypatch.setattr(publishing, "resolve_publisher", lambda platform, settings: FakePublisher())

    publishing.publish_post.apply(args=[post_id], task_id="manual-retry-task").get()

    with factory() as session:
        stored = session.get(Post, post.id)
        attempts = list(
            session.scalars(
                select(PublicationAttempt)
                .where(PublicationAttempt.post_id == post.id)
                .order_by(PublicationAttempt.attempt_no)
            )
        )
    assert stored.status is PostStatus.PUBLISHED
    assert [attempt.attempt_no for attempt in attempts] == [1, 2]
    assert [attempt.status for attempt in attempts] == [PublicationAttemptStatus.FAILED, PublicationAttemptStatus.SUCCESS]


def test_manual_retry_rejects_linkedin_post() -> None:
    session = make_session()
    project = Project(name="Manual retry project")
    item = ContentItem(project=project, title="LinkedIn item", content_type="educational")
    post = Post(content_item=item, platform=Platform.LINKEDIN, text="Manual", status=PostStatus.FAILED)
    session.add(post)
    session.commit()

    with pytest.raises(ConflictError, match="automatically"):
        queue_failed_post_for_manual_retry(session, post.id)


def test_task_publishes_once_and_duplicate_task_skips(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        post = make_post(
            session,
            status=PostStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        post_id = str(post.id)

    class FakePublisher:
        def publish(self, post: Post, media) -> publishing.PublicationResult:
            return publishing.PublicationResult("fake:123")

    monkeypatch.setattr(publishing, "get_session_factory", lambda: factory)
    monkeypatch.setattr(publishing, "get_publication_settings", lambda: PublicationSettings(_env_file=None))
    monkeypatch.setattr(publishing, "resolve_publisher", lambda platform, settings: FakePublisher())

    publishing.publish_post.apply(args=[post_id], task_id="task-a").get()
    publishing.publish_post.apply(args=[post_id], task_id="task-b").get()

    with factory() as session:
        stored = session.get(Post, post.id)
        attempts = list(session.scalars(select(PublicationAttempt).where(PublicationAttempt.post_id == post.id)))
    assert stored.status is PostStatus.PUBLISHED
    assert stored.external_post_id == "fake:123"
    assert len(attempts) == 1


def test_dispatch_queues_only_due_scheduled_ids(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        due = make_post(
            session,
            status=PostStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        make_post(
            session,
            status=PostStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        make_post(session, status=PostStatus.APPROVED, scheduled_at=None)

    queued: list[str] = []
    monkeypatch.setattr(scheduling, "get_session_factory", lambda: factory)
    monkeypatch.setattr(publishing.publish_post, "delay", queued.append)

    assert scheduling.dispatch_due_posts.run() == 1
    assert queued == [str(due.id)]
