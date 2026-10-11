"""Metadata for a post media asset; M1 does not create or manage files."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_pilot.db.base import Base
from content_pilot.models.enums import MediaSource, MediaType, database_enum
from content_pilot.models.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from content_pilot.models.post import Post


class MediaAsset(CreatedAtMixin, Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(
        database_enum(MediaType, "media_type"), nullable=False
    )
    source: Mapped[MediaSource] = mapped_column(
        database_enum(MediaSource, "media_source"), nullable=False
    )
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    post: Mapped[Post] = relationship(back_populates="media_assets")
