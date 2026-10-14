"""Short PostgreSQL transactions for the M4 publication lifecycle."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from content_pilot.models.enums import Platform, PostStatus, PublicationAttemptStatus
from content_pilot.models.post import Post
from content_pilot.models.publication_attempt import PublicationAttempt
from content_pilot.services.errors import ConflictError, NotFoundError


def _commit(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


def claim_scheduled_post(session: Session, post_id: object) -> bool:
    """Atomically claim a due scheduled post for one worker task."""
    result = session.execute(
        update(Post)
        .where(
            Post.id == post_id,
            Post.status == PostStatus.SCHEDULED,
            Post.scheduled_at <= datetime.now(timezone.utc),
        )
        .values(status=PostStatus.PUBLISHING)
        .returning(Post.id)
        .execution_options(synchronize_session=False)
    )
    claimed = result.scalar_one_or_none() is not None
    _commit(session)
    return claimed


def queue_failed_post_for_manual_retry(session: Session, post_id: object) -> Post:
    """Atomically make one failed VK/Telegram post eligible for the normal worker flow.

    The status compare-and-set prevents two form submissions from queuing two
    independent retries. The worker still performs the authoritative
    ``scheduled -> publishing`` claim before invoking a publisher.
    """
    post = session.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post not found")
    if post.status is not PostStatus.FAILED:
        raise ConflictError("Only a failed post can be retried manually")
    if post.platform not in {Platform.VK, Platform.TELEGRAM}:
        raise ConflictError("This platform cannot be published automatically")

    result = session.execute(
        update(Post)
        .where(
            Post.id == post_id,
            Post.status == PostStatus.FAILED,
            Post.platform.in_([Platform.VK, Platform.TELEGRAM]),
        )
        .values(
            status=PostStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc),
            last_error=None,
        )
        .returning(Post.id)
        .execution_options(synchronize_session=False)
    )
    if result.scalar_one_or_none() is None:
        session.rollback()
        raise ConflictError("The post is already being retried or its status has changed")
    _commit(session)
    session.refresh(post)
    return post


def task_owns_publishing_post(session: Session, post_id: object, task_id: str) -> bool:
    """Return whether this Celery task already owns a prior attempt."""
    return session.scalar(
        select(PublicationAttempt.id).where(
            PublicationAttempt.post_id == post_id,
            PublicationAttempt.celery_task_id == task_id,
        )
    ) is not None


def start_attempt(session: Session, post_id: object, task_id: str) -> PublicationAttempt:
    """Persist one publisher invocation after ownership was established."""
    next_no = (
        session.scalar(
            select(func.max(PublicationAttempt.attempt_no)).where(PublicationAttempt.post_id == post_id)
        )
        or 0
    ) + 1
    attempt = PublicationAttempt(post_id=post_id, attempt_no=next_no, celery_task_id=task_id)
    session.add(attempt)
    _commit(session)
    session.refresh(attempt)
    return attempt


def finish_success(
    session: Session,
    post_id: object,
    attempt_id: object,
    external_id: str | None,
) -> None:
    """Store a successful publication while preserving the scheduled history."""
    now = datetime.now(timezone.utc)
    session.execute(
        update(PublicationAttempt)
        .where(PublicationAttempt.id == attempt_id)
        .values(
            status=PublicationAttemptStatus.SUCCESS,
            finished_at=now,
            external_response_id=external_id,
        )
    )
    session.execute(
        update(Post)
        .where(Post.id == post_id, Post.status == PostStatus.PUBLISHING)
        .values(
            status=PostStatus.PUBLISHED,
            published_at=now,
            external_post_id=external_id,
            last_error=None,
        )
    )
    _commit(session)


def finish_failure(
    session: Session,
    post_id: object,
    attempt_id: object,
    error: str,
    final: bool,
) -> None:
    """Close an attempt and optionally mark the post as permanently failed."""
    safe_error = error[:1000]
    session.execute(
        update(PublicationAttempt)
        .where(PublicationAttempt.id == attempt_id)
        .values(
            status=PublicationAttemptStatus.FAILED,
            finished_at=datetime.now(timezone.utc),
            error=safe_error,
        )
    )
    if final:
        session.execute(
            update(Post)
            .where(Post.id == post_id, Post.status == PostStatus.PUBLISHING)
            .values(status=PostStatus.FAILED, last_error=safe_error)
        )
    _commit(session)
