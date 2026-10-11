"""Project model: the root of one content planning workspace."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_pilot.db.base import Base
from content_pilot.models.mixins import CreatedUpdatedAtMixin

if TYPE_CHECKING:
    from content_pilot.models.content_item import ContentItem
    from content_pilot.models.social_account import SocialAccount


class Project(CreatedUpdatedAtMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone_of_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="ru", nullable=False)

    social_accounts: Mapped[list[SocialAccount]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    content_items: Mapped[list[ContentItem]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
