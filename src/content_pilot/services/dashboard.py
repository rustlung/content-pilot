"""Read models used by the M3 dashboard without adding a repository framework."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, joinedload

from content_pilot.models.content_item import ContentItem
from content_pilot.models.enums import PostStatus
from content_pilot.models.post import Post
from content_pilot.models.project import Project


@dataclass(frozen=True)
class DashboardProjectSummary:
    id: UUID
    name: str
    language: str
    content_items_count: int
    posts_count: int
    scheduled_posts_count: int
    next_scheduled_at: datetime | None


def project_summaries(session: Session, limit: int = 6) -> list[DashboardProjectSummary]:
    """Return dashboard rows through two aggregate subqueries, not per-project loads."""
    now = datetime.now(timezone.utc)
    item_counts = (
        select(ContentItem.project_id.label("project_id"), func.count(ContentItem.id).label("content_items_count"))
        .group_by(ContentItem.project_id)
        .subquery()
    )
    post_counts = (
        select(
            ContentItem.project_id.label("project_id"),
            func.count(Post.id).label("posts_count"),
            func.coalesce(func.sum(case((Post.status == PostStatus.SCHEDULED, 1), else_=0)), 0).label("scheduled_posts_count"),
            func.min(
                case(
                    (and_(Post.status == PostStatus.SCHEDULED, Post.scheduled_at >= now), Post.scheduled_at),
                    else_=None,
                )
            ).label("next_scheduled_at"),
        )
        .join(Post, Post.content_item_id == ContentItem.id)
        .group_by(ContentItem.project_id)
        .subquery()
    )
    rows = session.execute(
        select(
            Project.id,
            Project.name,
            Project.language,
            func.coalesce(item_counts.c.content_items_count, 0),
            func.coalesce(post_counts.c.posts_count, 0),
            func.coalesce(post_counts.c.scheduled_posts_count, 0),
            post_counts.c.next_scheduled_at,
        )
        .outerjoin(item_counts, item_counts.c.project_id == Project.id)
        .outerjoin(post_counts, post_counts.c.project_id == Project.id)
        .order_by(Project.updated_at.desc())
        .limit(limit)
    ).all()
    return [DashboardProjectSummary(*row) for row in rows]


def dashboard_data(session: Session) -> dict[str, object]:
    counts = {
        "projects": session.scalar(select(func.count()).select_from(Project)) or 0,
        "content_items": session.scalar(select(func.count()).select_from(ContentItem)) or 0,
    }
    for status in PostStatus:
        counts[status.value] = session.scalar(
            select(func.count()).select_from(Post).where(Post.status == status)
        ) or 0
    upcoming = list(
        session.scalars(
            select(Post)
            .options(joinedload(Post.content_item).joinedload(ContentItem.project))
            .where(Post.status == PostStatus.SCHEDULED, Post.scheduled_at >= datetime.now(timezone.utc))
            .order_by(Post.scheduled_at)
            .limit(8)
        )
    )
    recent = list(
        session.scalars(
            select(Post)
            .options(joinedload(Post.content_item).joinedload(ContentItem.project))
            .order_by(Post.updated_at.desc())
            .limit(8)
        )
    )
    return {"counts": counts, "upcoming": upcoming, "recent": recent, "projects": project_summaries(session)}
