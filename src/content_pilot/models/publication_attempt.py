"""Publication-attempt persistence only; runtime execution arrives in a later M."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_pilot.db.base import Base
from content_pilot.models.enums import PublicationAttemptStatus, database_enum
from content_pilot.models.mixins import CreatedAtMixin, utc_now

if TYPE_CHECKING:
    from content_pilot.models.post import Post


class PublicationAttempt(CreatedAtMixin, Base):
    __tablename__ = "publication_attempts"
    __table_args__ = (
        UniqueConstraint("post_id", "attempt_no", name="post_attempt_no"),
        CheckConstraint("attempt_no > 0", name="attempt_no_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[PublicationAttemptStatus] = mapped_column(
        database_enum(PublicationAttemptStatus, "publication_attempt_status"),
        default=PublicationAttemptStatus.STARTED,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_response_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    post: Mapped[Post] = relationship(back_populates="publication_attempts")
