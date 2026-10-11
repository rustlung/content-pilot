"""Draft-only platform post generation."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from content_pilot.ai.prompts import post_prompt
from content_pilot.ai.service import AIProvider
from content_pilot.models.content_item import ContentItem
from content_pilot.models.enums import Platform, PostStatus
from content_pilot.models.post import Post
from content_pilot.services.errors import ConflictError, NotFoundError


def generate_post(session: Session, provider: AIProvider, content_item_id: object, platform: Platform, instructions: str | None = None) -> Post:
    item = session.scalar(select(ContentItem).options(joinedload(ContentItem.project)).where(ContentItem.id == content_item_id))
    if item is None:
        raise NotFoundError("Content item not found")
    prompt = post_prompt(item.project, item, platform, instructions)
    session.rollback()
    generated = provider.generate_post(prompt)
    existing = session.scalar(select(Post).where(Post.content_item_id == content_item_id, Post.platform == platform))
    if existing is not None and existing.status is not PostStatus.DRAFT:
        raise ConflictError("Cannot regenerate a non-draft post")
    post = existing or Post(content_item_id=content_item_id, platform=platform, status=PostStatus.DRAFT)
    post.text = generated.text
    if existing is None:
        session.add(post)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(post)
    return post


def list_posts(session: Session, content_item_id: object) -> list[Post]:
    if session.get(ContentItem, content_item_id) is None:
        raise NotFoundError("Content item not found")
    return list(session.scalars(select(Post).where(Post.content_item_id == content_item_id)))
