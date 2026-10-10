"""Content-plan item model, distinct from a publishable post."""
from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_pilot.db.base import Base
from content_pilot.models.enums import ContentItemStatus
from content_pilot.models.mixins import CreatedUpdatedAtMixin

if TYPE_CHECKING:
    from content_pilot.models.post import Post
    from content_pilot.models.project import Project


class ContentItem(CreatedUpdatedAtMixin, Base):
    __tablename__ = "content_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    planned_date: Mapped[date | None] = mapped_column(nullable=True)
    status: Mapped[ContentItemStatus] = mapped_column(
        Enum(ContentItemStatus, native_enum=False, create_constraint=True, name="content_item_status"),
        default=ContentItemStatus.DRAFT,
        nullable=False,
    )

    project: Mapped[Project] = relationship(back_populates="content_items")
    posts: Mapped[list[Post]] = relationship(back_populates="content_item", cascade="all, delete-orphan")
