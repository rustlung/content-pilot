"""Small provider-neutral contract for M4/M5 publication tasks."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Sequence

from content_pilot.models.media_asset import MediaAsset
from content_pilot.models.post import Post


class PublisherRetryableError(Exception):
    """A temporary provider condition that can be retried by Celery."""


class PublisherPermanentError(Exception):
    """A provider rejected a request that should not be retried."""


class PublisherUnavailableError(PublisherPermanentError):
    """Required publisher configuration or a supported adapter is unavailable."""


@dataclass(frozen=True)
class PublicationResult:
    external_post_id: str | None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PublicationMedia:
    """A MediaAsset with an already validated local path."""

    asset_id: uuid.UUID
    media_type: str
    path: Path


class Publisher(Protocol):
    def publish(self, post: Post, media: Sequence[PublicationMedia]) -> PublicationResult:
        """Publish a post without receiving a database session."""
