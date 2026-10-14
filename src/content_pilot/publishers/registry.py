"""Small platform-to-publisher resolver for the M4 task pipeline."""
from __future__ import annotations

import uuid
from typing import Sequence

from content_pilot.config import PublicationSettings
from content_pilot.models.enums import Platform
from content_pilot.models.post import Post
from content_pilot.publishers.base import (
    PublicationMedia,
    PublicationResult,
    Publisher,
    PublisherUnavailableError,
)
from content_pilot.publishers.telegram import TelegramPublisher
from content_pilot.publishers.vk import VkPublisher


class DryRunPublisher:
    """Safe local publisher used only by explicit development/test configuration."""

    def publish(self, post: Post, media: Sequence[PublicationMedia]) -> PublicationResult:
        return PublicationResult(f"dry-run:{uuid.uuid4()}")


def resolve_publisher(platform: Platform, settings: PublicationSettings) -> Publisher:
    if settings.publishing_dry_run and settings.app_env in {"development", "test"}:
        return DryRunPublisher()
    if platform is Platform.TELEGRAM:
        return TelegramPublisher(settings)
    if platform is Platform.VK:
        return VkPublisher(settings)
    raise PublisherUnavailableError("LinkedIn is available for manual publication only")
