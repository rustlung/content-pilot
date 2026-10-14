"""Official VK community text publisher; image upload is intentionally unsupported."""
from __future__ import annotations

from contextlib import nullcontext
import logging
from typing import Any, Iterator, Sequence

import httpx

from content_pilot.config import PublicationSettings
from content_pilot.models.post import Post
from content_pilot.publishers.base import (
    PublicationMedia,
    PublicationResult,
    PublisherPermanentError,
    PublisherRetryableError,
    PublisherUnavailableError,
)

logger = logging.getLogger(__name__)


class VkPublisher:
    def __init__(self, settings: PublicationSettings, http_client: httpx.Client | None = None) -> None:
        if settings.vk_access_token is None or not settings.vk_group_id:
            raise PublisherUnavailableError("VK publisher is not configured")
        try:
            group_id = int(settings.vk_group_id)
        except ValueError as error:
            raise PublisherUnavailableError("VK group id must be numeric") from error
        if group_id <= 0:
            raise PublisherUnavailableError("VK group id must be positive")
        self._token = settings.vk_access_token.get_secret_value()
        self._group_id = group_id
        self._api_version = settings.vk_api_version
        self._timeout = settings.social_http_timeout_seconds
        self._http_client = http_client

    def _client(self) -> Iterator[httpx.Client]:
        if self._http_client is not None:
            return nullcontext(self._http_client)
        return httpx.Client(timeout=self._timeout)

    def publish(self, post: Post, media: Sequence[PublicationMedia]) -> PublicationResult:
        text = (post.text or "").strip()
        if not text:
            raise PublisherPermanentError("Post text must not be blank")
        data: dict[str, Any] = {
            "access_token": self._token,
            "v": self._api_version,
            "owner_id": -self._group_id,
            "from_group": 1,
            "message": text,
        }
        try:
            with self._client() as client:
                response = client.post("https://api.vk.com/method/wall.post", data=data)
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise PublisherRetryableError("VK network request failed") from error

        if response.status_code == 429 or response.status_code >= 500:
            raise PublisherRetryableError("VK temporarily unavailable")
        if response.status_code >= 400:
            raise PublisherPermanentError("VK rejected the publication request")
        try:
            payload = response.json()
        except ValueError as error:
            raise PublisherPermanentError("VK returned an invalid response") from error
        if not isinstance(payload, dict):
            raise PublisherPermanentError("VK returned an invalid response")
        if "error" in payload:
            error = payload["error"]
            error_code = error.get("error_code") if isinstance(error, dict) else None
            error_message = error.get("error_msg") if isinstance(error, dict) else None
            safe_message = _safe_error_message(error_message)
            safe_code = error_code if isinstance(error_code, int) else "unknown"
            logger.warning('VK API error code=%s message="%s"', safe_code, safe_message)
            if isinstance(error_code, int):
                raise PublisherPermanentError(f"VK rejected the publication request (code {error_code})")
            raise PublisherPermanentError("VK rejected the publication request")
        response_data = payload.get("response")
        if not isinstance(response_data, dict) or not isinstance(response_data.get("post_id"), int):
            raise PublisherPermanentError("VK response has no post identifier")

        warnings: tuple[str, ...] = ()
        if media:
            warnings = ("VK image upload is unavailable; publish attached media manually.",)
        external_id = f"vk:wall-{self._group_id}_{response_data['post_id']}"
        return PublicationResult(external_id, warnings=warnings)


def _safe_error_message(value: object) -> str:
    """Return diagnostic text suitable for logs without retaining raw payloads."""
    if not isinstance(value, str) or not value.strip():
        return "No message"
    return " ".join(value.split()).replace('"', "'")[:500]
