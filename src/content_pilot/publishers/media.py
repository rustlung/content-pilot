"""Safe conversion of stored relative media paths into local files."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from content_pilot.models.media_asset import MediaAsset
from content_pilot.publishers.base import PublicationMedia, PublisherPermanentError


def resolve_publication_media(media: Sequence[MediaAsset], media_root: Path) -> list[PublicationMedia]:
    root = media_root.resolve()
    resolved: list[PublicationMedia] = []
    for asset in media:
        relative_path = Path(asset.file_path)
        if relative_path.is_absolute():
            raise PublisherPermanentError("Stored media path must be relative")
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise PublisherPermanentError("Stored media path is outside MEDIA_ROOT") from error
        if not candidate.is_file():
            raise PublisherPermanentError("Generated media file is unavailable")
        resolved.append(
            PublicationMedia(asset_id=asset.id, media_type=asset.media_type.value, path=candidate)
        )
    return resolved
