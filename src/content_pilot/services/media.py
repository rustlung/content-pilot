"""Local M2 image generation and safe filesystem persistence."""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from content_pilot.ai.prompts import image_prompt
from content_pilot.ai.service import AIProvider
from content_pilot.models.enums import MediaSource, MediaType
from content_pilot.models.content_item import ContentItem
from content_pilot.models.media_asset import MediaAsset
from content_pilot.models.post import Post
from content_pilot.services.errors import NotFoundError


def _post_with_context(session: Session, post_id: object) -> Post:
    post = session.scalar(
        select(Post).options(joinedload(Post.content_item).joinedload(ContentItem.project)).where(Post.id == post_id)
    )
    if post is None:
        raise NotFoundError("Post not found")
    return post


def generate_image_prompt(session: Session, provider: AIProvider, post_id: object):
    post = _post_with_context(session, post_id)
    if not post.text:
        raise ValueError("Post text is required before generating an image")
    prompt = image_prompt(post.content_item.project, post.content_item, post.text, post.platform)
    session.rollback()
    return provider.generate_image_prompt(prompt)


def generate_image(session: Session, provider: AIProvider, post_id: object, media_root: Path) -> MediaAsset:
    post = _post_with_context(session, post_id)
    if not post.text:
        raise ValueError("Post text is required before generating an image")
    request_prompt = image_prompt(post.content_item.project, post.content_item, post.text, post.platform)
    project_id = post.content_item.project_id
    session.rollback()
    generated_prompt = provider.generate_image_prompt(request_prompt)
    image_data = provider.generate_image(generated_prompt.prompt)
    if not image_data:
        raise ValueError("AI returned an empty image")
    relative_path = Path(str(project_id)) / str(post_id) / f"{uuid.uuid4()}.png"
    destination = media_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.write_bytes(image_data)
    except OSError:
        raise
    asset = MediaAsset(
        post_id=post_id,
        media_type=MediaType.IMAGE,
        source=MediaSource.AI,
        file_path=relative_path.as_posix(),
        prompt=generated_prompt.prompt,
    )
    try:
        session.add(asset)
        session.commit()
        session.refresh(asset)
    except Exception:
        session.rollback()
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return asset


def list_media(session: Session, post_id: object) -> list[MediaAsset]:
    if session.get(Post, post_id) is None:
        raise NotFoundError("Post not found")
    return list(session.scalars(select(MediaAsset).where(MediaAsset.post_id == post_id)))


def get_media_asset(session: Session, media_id: object) -> MediaAsset:
    """Return one asset with its post, without exposing a stored filesystem path."""
    asset = session.scalar(
        select(MediaAsset).options(joinedload(MediaAsset.post)).where(MediaAsset.id == media_id)
    )
    if asset is None:
        raise NotFoundError("Изображение не найдено")
    return asset


def resolve_media_file(asset: MediaAsset, media_root: Path) -> Path:
    """Resolve a stored relative path only when it remains a regular file under MEDIA_ROOT."""
    if not asset.file_path:
        raise NotFoundError("Файл изображения недоступен")

    relative_path = Path(asset.file_path)
    if relative_path.is_absolute():
        raise NotFoundError("Файл изображения недоступен")

    root = media_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise NotFoundError("Файл изображения недоступен") from error
    if not candidate.is_file():
        raise NotFoundError("Файл изображения недоступен")
    return candidate
