"""Telegram publisher for direct Bot API and the ContentPilot Gateway."""
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
        self._gateway_base_url = settings.telegram_gateway_base_url
        self._gateway_key: str | None = None
        self._token: str | None = None
        self._chat_id: str | None = None

        if self._gateway_base_url:
            if settings.contentpilot_gateway_key is None:
                raise PublisherUnavailableError("Telegram Gateway key is not configured")
            self._gateway_key = settings.contentpilot_gateway_key.get_secret_value()
        elif settings.contentpilot_gateway_key is not None:
            raise PublisherUnavailableError("Telegram Gateway URL is not configured")
        elif settings.telegram_bot_token is None or not settings.telegram_chat_id:
            raise PublisherUnavailableError("Telegram publisher is not configured")
        else:
            self._token = settings.telegram_bot_token.get_secret_value()
            self._chat_id = settings.telegram_chat_id

        self._timeout = settings.social_http_timeout_seconds
        self._http_client = http_client

    def _client(self) -> Iterator[httpx.Client]:
        if self._http_client is not None:
            return nullcontext(self._http_client)
        return httpx.Client(timeout=self._timeout)

    def _url(self, method: str) -> str:
        if self._gateway_base_url:
            return f"{self._gateway_base_url}/contentpilot/{method}"
        assert self._token is not None
        return f"https://api.telegram.org/bot{self._token}/{method}"

    def _call(self, method: str, *, data: dict[str, str], files: Any = None) -> int:
        try:
            with self._client() as client:
                if self._gateway_base_url:
                    assert self._gateway_key is not None
                    headers = {"Authorization": f"Bearer {self._gateway_key}"}
                    if files is None:
                        response = client.post(self._url(method), json=data, headers=headers)
                    else:
                        response = client.post(self._url(method), data=data, files=files, headers=headers)
                else:
                    response = client.post(self._url(method), data=data, files=files)
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise PublisherRetryableError("Telegram network request failed") from error

        effective_status = self._gateway_provider_status(response) or response.status_code
        if effective_status == 429 or effective_status >= 500:
            raise PublisherRetryableError("Telegram temporarily unavailable")
        if effective_status >= 400:
            raise PublisherPermanentError("Telegram rejected the publication request")
        try:
            payload = response.json()
        except ValueError as error:
            raise PublisherPermanentError("Telegram returned an invalid response") from error
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            error_code = self._payload_status(payload)
            if error_code == 429 or (isinstance(error_code, int) and error_code >= 500):
                raise PublisherRetryableError("Telegram rate limit reached")
            raise PublisherPermanentError("Telegram rejected the publication request")
        message_id = self._message_id(payload)
        if message_id is None:
            raise PublisherPermanentError("Telegram response has no message identifier")
        return message_id

    def _gateway_provider_status(self, response: httpx.Response) -> int | None:
        """Read a gateway-wrapped Telegram status without exposing its payload."""
        if not self._gateway_base_url or response.status_code != 502:
            return None
        try:
            return self._payload_status(response.json())
        except ValueError:
            return None

    @staticmethod
    def _payload_status(payload: object) -> int | None:
        if not isinstance(payload, dict):
            return None
        for field in ("status", "error_code"):
            value = payload.get(field)
            if isinstance(value, int):
                return value
        return None

    @staticmethod
    def _message_id(payload: dict[str, Any]) -> int | None:
        gateway_message_id = payload.get("message_id")
        if isinstance(gateway_message_id, int):
            return gateway_message_id
        result = payload.get("result")
        if isinstance(result, dict) and isinstance(result.get("message_id"), int):
            return result["message_id"]
        return None

    def _external_post_id(self, message_id: int) -> str:
        if self._gateway_base_url:
            return f"telegram:gateway:{message_id}"
        assert self._chat_id is not None
        return f"telegram:{self._chat_id}:{message_id}"

    def publish(self, post: Post, media: Sequence[PublicationMedia]) -> PublicationResult:
        text = (post.text or "").strip()
        if not text:
            raise PublisherPermanentError("Post text must not be blank")
        image = next((item for item in media if item.media_type == "image"), None)
        if image is None:
            data = {"text": text} if self._gateway_base_url else {"chat_id": self._chat_id or "", "text": text}
            message_id = self._call("sendMessage", data=data)
            return PublicationResult(self._external_post_id(message_id))

        caption = text if len(text) <= TELEGRAM_CAPTION_LIMIT else ""
        photo_data = (
            {"caption": caption} if caption else {}
        ) if self._gateway_base_url else {"chat_id": self._chat_id or "", "caption": caption}
        try:
            with image.path.open("rb") as image_file:
                photo_message_id = self._call(
                    "sendPhoto",
                    data=photo_data,
                    files={"photo": (image.path.name, image_file, "image/png")},
                )
        except OSError as error:
            raise PublisherPermanentError("Generated media file is unavailable") from error

        if caption:
            return PublicationResult(self._external_post_id(photo_message_id))
        text_data = {"text": text} if self._gateway_base_url else {"chat_id": self._chat_id or "", "text": text}
        text_message_id = self._call("sendMessage", data=text_data)
        if self._gateway_base_url:
            return PublicationResult(self._external_post_id(text_message_id))
        assert self._chat_id is not None
        return PublicationResult(
            f"telegram:{self._chat_id}:photo:{photo_message_id}:text:{text_message_id}"
        )
