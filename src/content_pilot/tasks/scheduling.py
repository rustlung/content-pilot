"""Beat-triggered due-post dispatcher."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from content_pilot.db.session import get_session_factory
from content_pilot.models.enums import PostStatus
from content_pilot.models.post import Post
from content_pilot.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="content_pilot.dispatch_due_posts")
def dispatch_due_posts() -> int:
    with get_session_factory()() as session:
        ids = list(
            session.scalars(
                select(Post.id).where(
                    Post.status == PostStatus.SCHEDULED,
                    Post.scheduled_at <= datetime.now(timezone.utc),
                )
            )
        )
    for post_id in ids:
        from content_pilot.tasks.publishing import publish_post
        publish_post.delay(str(post_id))
    logger.info("dispatch_due_posts due=%s queued=%s", len(ids), len(ids))
    return len(ids)
