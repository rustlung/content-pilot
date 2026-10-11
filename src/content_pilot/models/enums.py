"""Closed foundation values for the ContentPilot data model."""
from enum import Enum

from sqlalchemy import Enum as SqlEnum


def database_enum(enum_class: type[Enum], name: str) -> SqlEnum:
    """Persist lowercase enum values, matching the portable M1 check constraints."""
    return SqlEnum(
        enum_class,
        native_enum=False,
        create_constraint=True,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class Platform(str, Enum):
    LINKEDIN = "linkedin"
    VK = "vk"
    TELEGRAM = "telegram"


class ContentItemStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    CANCELLED = "cancelled"


class PostStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaType(str, Enum):
    IMAGE = "image"


class MediaSource(str, Enum):
    AI = "ai"
    MANUAL = "manual"


class PublicationAttemptStatus(str, Enum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
