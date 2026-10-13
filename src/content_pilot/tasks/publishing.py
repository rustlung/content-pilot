"""Celery orchestration for publisher adapters; state remains in PostgreSQL."""
from __future__ import annotations

import logging
import uuid

from celery import Task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from content_pilot.config import Settings
from content_pilot.db.session import get_session_factory
from content_pilot.models.enums import PostStatus
from content_pilot.models.post import Post
from content_pilot.publishers.base import (
    PublicationResult,
    PublisherPermanentError,
    PublisherRetryableError,
    PublisherUnavailableError,
)
from content_pilot.publishers.media import resolve_publication_media
from content_pilot.publishers.registry import resolve_publisher
from content_pilot.services.publication import (
    claim_scheduled_post,
    finish_failure,
    finish_success,
    start_attempt,
    task_owns_publishing_post,
)
from content_pilot.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _load_post_for_publication(session, post_id: uuid.UUID) -> Post | None:
    return session.scalar(
        select(Post).options(selectinload(Post.media_assets)).where(Post.id == post_id)
    )


@celery_app.task(bind=True, name="content_pilot.publish_post", max_retries=None)
def publish_post(self: Task, post_id: str) -> None:
    settings = Settings()
    task_id = self.request.id or "unknown"
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        logger.info("publish_post skipped invalid post_id task_id=%s", task_id)
        return

    with get_session_factory()() as session:
        post = session.get(Post, post_uuid)
        if post is None:
            logger.info("publish_post skipped missing post_id=%s task_id=%s", post_id, task_id)
            return
        claimed = claim_scheduled_post(session, post_uuid)
        if not claimed:
            session.refresh(post)
            if post.status is not PostStatus.PUBLISHING or not task_owns_publishing_post(session, post_uuid, task_id):
                logger.info("publish_post skipped post_id=%s task_id=%s", post_id, task_id)
                return
        attempt = start_attempt(session, post_uuid, task_id)
        post = _load_post_for_publication(session, post_uuid)
        assert post is not None

    try:
        media = resolve_publication_media(post.media_assets, settings.media_root)
        result = resolve_publisher(post.platform, settings).publish(post, media)
    except PublisherRetryableError as error:
        with get_session_factory()() as session:
            final = self.request.retries >= settings.publication_max_retries
            finish_failure(session, post_uuid, attempt.id, str(error), final)
        if final:
            logger.info("publish_post retries exhausted post_id=%s task_id=%s", post_id, task_id)
            return
        countdown = settings.publication_retry_base_seconds * (2**self.request.retries)
        logger.info(
            "publish_post retry post_id=%s platform=%s task_id=%s attempt=%s countdown=%s",
            post_id,
            post.platform.value,
            task_id,
            attempt.attempt_no,
            countdown,
        )
        raise self.retry(exc=error, countdown=countdown, max_retries=settings.publication_max_retries)
    except (PublisherPermanentError, PublisherUnavailableError) as error:
        with get_session_factory()() as session:
            finish_failure(session, post_uuid, attempt.id, str(error), True)
        logger.info("publish_post failed post_id=%s platform=%s task_id=%s", post_id, post.platform.value, task_id)
        return

    with get_session_factory()() as session:
        finish_success(session, post_uuid, attempt.id, result.external_post_id)
    if result.warnings:
        logger.info("publish_post success with capability warning post_id=%s platform=%s", post_id, post.platform.value)
    logger.info(
        "publish_post success post_id=%s platform=%s task_id=%s attempt=%s",
        post_id,
        post.platform.value,
        task_id,
        attempt.attempt_no,
    )
