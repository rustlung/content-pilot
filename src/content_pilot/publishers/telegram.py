"""Official Telegram Bot API publisher using direct HTTP requests."""
from __future__ import annotations

from contextlib import nullcontext
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

TELEGRAM_CAPTION_LIMIT = 1024


class TelegramPublisher:
    def __init__(self, settings: PublicationSettings, http_client: httpx.Client | None = None) -> None:
        if settings.telegram_bot_token is None or not settings.telegram_chat_id:
            raise PublisherUnavailableError("Telegram publisher is not configured")
        self._token = settings.telegram_bot_token.get_secret_value()
        self._chat_id = settings.telegram_chat_id
        self._timeout = settings.social_http_timeout_seconds
        self._http_client = http_client

    def _client(self) -> Iterator[httpx.Client]:
        if self._http_client is not None:
            return nullcontext(self._http_client)
        return httpx.Client(timeout=self._timeout)

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"

    def _call(self, method: str, *, data: dict[str, str], files: Any = None) -> dict[str, Any]:
        try:
            with self._client() as client:
                response = client.post(self._url(method), data=data, files=files)
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise PublisherRetryableError("Telegram network request failed") from error

        if response.status_code == 429 or response.status_code >= 500:
            raise PublisherRetryableError("Telegram temporarily unavailable")
        if response.status_code >= 400:
            raise PublisherPermanentError("Telegram rejected the publication request")
        try:
            payload = response.json()
        except ValueError as error:
            raise PublisherPermanentError("Telegram returned an invalid response") from error
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            error_code = payload.get("error_code") if isinstance(payload, dict) else None
            if error_code == 429:
                raise PublisherRetryableError("Telegram rate limit reached")
            raise PublisherPermanentError("Telegram rejected the publication request")
        result = payload.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("message_id"), int):
            raise PublisherPermanentError("Telegram response has no message identifier")
        return result

    def publish(self, post: Post, media: Sequence[PublicationMedia]) -> PublicationResult:
        text = (post.text or "").strip()
        if not text:
            raise PublisherPermanentError("Post text must not be blank")
        image = next((item for item in media if item.media_type == "image"), None)
        if image is None:
            sent = self._call("sendMessage", data={"chat_id": self._chat_id, "text": text})
            return PublicationResult(f"telegram:{self._chat_id}:{sent['message_id']}")

        caption = text if len(text) <= TELEGRAM_CAPTION_LIMIT else ""
        try:
            with image.path.open("rb") as image_file:
                sent_photo = self._call(
                    "sendPhoto",
                    data={"chat_id": self._chat_id, "caption": caption},
                    files={"photo": (image.path.name, image_file, "image/png")},
                )
        except OSError as error:
            raise PublisherPermanentError("Generated media file is unavailable") from error

        if caption:
            return PublicationResult(f"telegram:{self._chat_id}:{sent_photo['message_id']}")
        sent_text = self._call("sendMessage", data={"chat_id": self._chat_id, "text": text})
        return PublicationResult(
            f"telegram:{self._chat_id}:photo:{sent_photo['message_id']}:text:{sent_text['message_id']}"
        )
