"""Social account identity, deliberately without credentials in M1."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_pilot.db.base import Base
from content_pilot.models.enums import Platform, database_enum
from content_pilot.models.mixins import CreatedUpdatedAtMixin

if TYPE_CHECKING:
    from content_pilot.models.project import Project


class SocialAccount(CreatedUpdatedAtMixin, Base):
    __tablename__ = "social_accounts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[Platform] = mapped_column(
        database_enum(Platform, "platform"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    project: Mapped[Project] = relationship(back_populates="social_accounts")
