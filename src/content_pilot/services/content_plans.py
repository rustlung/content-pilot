"""Atomic content-plan generation after a short, provider-free DB read."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from content_pilot.ai.prompts import content_plan_prompt
from content_pilot.ai.service import AIProvider
from content_pilot.models.content_item import ContentItem
from content_pilot.models.enums import Platform
from content_pilot.models.project import Project
from content_pilot.services.errors import NotFoundError, ValidationDomainError


def generate_content_plan(session: Session, provider: AIProvider, project_id: object, start_date: date, end_date: date, posts_count: int, platforms: list[Platform]) -> list[ContentItem]:
    if start_date > end_date:
        raise ValidationDomainError("start_date must not be after end_date")
    if not 1 <= posts_count <= 100:
        raise ValidationDomainError("posts_count must be between 1 and 100")
    if not platforms:
        raise ValidationDomainError("at least one platform is required")
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    prompt = content_plan_prompt(project, start_date, end_date, posts_count, platforms)
    session.rollback()
    plan = provider.generate_content_plan(prompt)
    if len(plan.items) != posts_count:
        raise ValidationDomainError("AI returned a different number of plan items")
    if any(item.suggested_date < start_date or item.suggested_date > end_date for item in plan.items):
        raise ValidationDomainError("AI returned an item outside the requested period")
    items = [
        ContentItem(project_id=project_id, title=item.title, topic=item.topic, goal=item.goal.value, content_type=item.content_type.value, planned_date=item.suggested_date)
        for item in plan.items
    ]
    try:
        session.add_all(items)
        session.commit()
    except Exception:
        session.rollback()
        raise
    for item in items:
        session.refresh(item)
    return items


def list_content_items(session: Session, project_id: object) -> list[ContentItem]:
    if session.get(Project, project_id) is None:
        raise NotFoundError("Project not found")
    return list(session.scalars(select(ContentItem).where(ContentItem.project_id == project_id).order_by(ContentItem.planned_date, ContentItem.created_at)))
