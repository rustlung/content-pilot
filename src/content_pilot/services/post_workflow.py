"""Application-level manual workflow; Celery owns M4 publication execution."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from content_pilot.models.enums import PostStatus
from content_pilot.models.enums import Platform
from content_pilot.models.post import Post
from content_pilot.services.errors import ConflictError, NotFoundError, ValidationDomainError


def _post(session: Session, post_id: object) -> Post:
    post = session.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post not found")
    return post


def _commit(session: Session, post: Post) -> Post:
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(post)
    return post


def approve_post(session: Session, post_id: object) -> Post:
    post = _post(session, post_id)
    if post.status is not PostStatus.DRAFT:
        raise ConflictError("Only a draft post can be approved")
    if not post.text or not post.text.strip():
        raise ValidationDomainError("Post text must not be blank")
    post.status = PostStatus.APPROVED
    return _commit(session, post)


def schedule_post(session: Session, post_id: object, scheduled_at: datetime) -> Post:
    post = _post(session, post_id)
    if post.status is not PostStatus.APPROVED:
        raise ConflictError("Only an approved post can be scheduled")
    if post.platform is Platform.LINKEDIN:
        raise ConflictError("LinkedIn posts are published manually and cannot be scheduled automatically")
    if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
        raise ValidationDomainError("scheduled_at must be timezone-aware")
    scheduled_utc = scheduled_at.astimezone(timezone.utc)
    if scheduled_utc <= datetime.now(timezone.utc):
        raise ValidationDomainError("scheduled_at must be in the future")
    post.scheduled_at = scheduled_utc
    post.status = PostStatus.SCHEDULED
    return _commit(session, post)


def unschedule_post(session: Session, post_id: object) -> Post:
    post = _post(session, post_id)
    if post.status is not PostStatus.SCHEDULED:
        raise ConflictError("Only a scheduled post can be unscheduled")
    post.scheduled_at = None
    post.status = PostStatus.APPROVED
    return _commit(session, post)


def return_post_to_draft(session: Session, post_id: object) -> Post:
    """Reopen an approved or failed post without losing its publication history."""
    post = _post(session, post_id)
    if post.status not in {PostStatus.APPROVED, PostStatus.FAILED}:
        raise ConflictError("Only an approved or failed post can be returned to draft")

    post.status = PostStatus.DRAFT
    post.scheduled_at = None
    post.published_at = None
    post.external_post_id = None
    post.last_error = None
    return _commit(session, post)


def cancel_post(session: Session, post_id: object) -> Post:
    post = _post(session, post_id)
    if post.status not in {PostStatus.DRAFT, PostStatus.APPROVED, PostStatus.SCHEDULED}:
        raise ConflictError("This post cannot be cancelled")
    post.status = PostStatus.CANCELLED
    post.scheduled_at = None
    return _commit(session, post)
