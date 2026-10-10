"""Closed foundation values for the ContentPilot data model."""
from enum import Enum


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
