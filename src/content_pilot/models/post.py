"""Platform-specific post model; workflow logic belongs to later milestones."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_pilot.db.base import Base
from content_pilot.models.enums import Platform, PostStatus, database_enum
from content_pilot.models.mixins import CreatedUpdatedAtMixin

if TYPE_CHECKING:
    from content_pilot.models.content_item import ContentItem
    from content_pilot.models.media_asset import MediaAsset
    from content_pilot.models.publication_attempt import PublicationAttempt


class Post(CreatedUpdatedAtMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("content_item_id", "platform", name="content_item_platform"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[Platform] = mapped_column(
        database_enum(Platform, "platform"), nullable=False
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PostStatus] = mapped_column(
        database_enum(PostStatus, "post_status"),
        default=PostStatus.DRAFT,
        nullable=False,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    content_item: Mapped[ContentItem] = relationship(back_populates="posts")
    media_assets: Mapped[list[MediaAsset]] = relationship(back_populates="post", cascade="all, delete-orphan")
    publication_attempts: Mapped[list[PublicationAttempt]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
