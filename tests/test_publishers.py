"""M5 publisher adapters use httpx MockTransport only; no real post is sent."""
from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from content_pilot.config import Settings
from content_pilot.models.enums import Platform
from content_pilot.models.post import Post
from content_pilot.publishers.base import (
    PublicationMedia,
    PublisherPermanentError,
    PublisherRetryableError,
    PublisherUnavailableError,
)
from content_pilot.publishers.media import resolve_publication_media
from content_pilot.publishers.registry import DryRunPublisher, resolve_publisher
from content_pilot.publishers.telegram import TELEGRAM_CAPTION_LIMIT, TelegramPublisher
from content_pilot.publishers.vk import VkPublisher


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "postgres_password": "test-password",
        "app_env": "test",
        "telegram_bot_token": "telegram-token",
        "telegram_chat_id": "-100123",
        "vk_access_token": "vk-token",
        "vk_group_id": "42",
    }
    values.update(overrides)
    return Settings(**values)


def post(platform: Platform, text: str = "Тестовый текст") -> Post:
    return Post(platform=platform, text=text, content_item_id=uuid.uuid4())


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_telegram_text_post_returns_message_identifier() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/sendMessage")
        assert parse_qs(request.content.decode())["text"] == ["Тестовый текст"]
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 17}})

    result = TelegramPublisher(settings(), client(handler)).publish(post(Platform.TELEGRAM), [])
    assert result.external_post_id == "telegram:-100123:17"


def test_telegram_image_caption_post(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    image.write_bytes(b"image")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/sendPhoto")
        assert "Тестовый текст".encode() in request.content
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 18}})

    media = [PublicationMedia(uuid.uuid4(), "image", image)]
    result = TelegramPublisher(settings(), client(handler)).publish(post(Platform.TELEGRAM), media)
    assert result.external_post_id == "telegram:-100123:18"


def test_telegram_long_text_sends_photo_then_full_message(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    image.write_bytes(b"image")
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path.rsplit("/", 1)[-1])
        message_id = 19 if calls[-1] == "sendPhoto" else 20
        return httpx.Response(200, json={"ok": True, "result": {"message_id": message_id}})

    long_text = "т" * (TELEGRAM_CAPTION_LIMIT + 1)
    media = [PublicationMedia(uuid.uuid4(), "image", image)]
    result = TelegramPublisher(settings(), client(handler)).publish(post(Platform.TELEGRAM, long_text), media)
    assert calls == ["sendPhoto", "sendMessage"]
    assert result.external_post_id == "telegram:-100123:photo:19:text:20"


@pytest.mark.parametrize("status", [429, 500])
def test_telegram_transient_http_failures_are_retryable(status: int) -> None:
    publisher = TelegramPublisher(settings(), client(lambda request: httpx.Response(status, json={})))
    with pytest.raises(PublisherRetryableError):
        publisher.publish(post(Platform.TELEGRAM), [])


def test_telegram_auth_failure_is_permanent() -> None:
    publisher = TelegramPublisher(settings(), client(lambda request: httpx.Response(401, json={})))
    with pytest.raises(PublisherPermanentError):
        publisher.publish(post(Platform.TELEGRAM), [])


def test_telegram_timeout_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    publisher = TelegramPublisher(settings(), client(handler))
    with pytest.raises(PublisherRetryableError):
        publisher.publish(post(Platform.TELEGRAM), [])


def test_telegram_invalid_response_is_permanent() -> None:
    publisher = TelegramPublisher(settings(), client(lambda request: httpx.Response(200, text="not-json")))
    with pytest.raises(PublisherPermanentError):
        publisher.publish(post(Platform.TELEGRAM), [])


def test_vk_posts_as_community_and_keeps_media_manual() -> None:
    captured: dict[str, list[str]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/method/wall.post")
        captured.update(parse_qs(request.content.decode()))
        return httpx.Response(200, json={"response": {"post_id": 99}})

    media = [PublicationMedia(uuid.uuid4(), "image", Path("unused.png"))]
    result = VkPublisher(settings(), client(handler)).publish(post(Platform.VK), media)
    assert captured["owner_id"] == ["-42"]
    assert captured["from_group"] == ["1"]
    assert captured["v"] == ["5.199"]
    assert result.external_post_id == "vk:wall-42_99"
    assert result.warnings


@pytest.mark.parametrize("status", [429, 502])
def test_vk_transient_http_failures_are_retryable(status: int) -> None:
    publisher = VkPublisher(settings(), client(lambda request: httpx.Response(status, json={})))
    with pytest.raises(PublisherRetryableError):
        publisher.publish(post(Platform.VK), [])


def test_vk_api_error_is_permanent() -> None:
    publisher = VkPublisher(settings(), client(lambda request: httpx.Response(200, json={"error": {"error_code": 15}})))
    with pytest.raises(PublisherPermanentError):
        publisher.publish(post(Platform.VK), [])


def test_registry_prefers_dry_run_and_rejects_linkedin() -> None:
    assert isinstance(resolve_publisher(Platform.VK, settings(publishing_dry_run=True)), DryRunPublisher)
    assert isinstance(resolve_publisher(Platform.TELEGRAM, settings()), TelegramPublisher)
    assert isinstance(resolve_publisher(Platform.VK, settings()), VkPublisher)
    with pytest.raises(PublisherUnavailableError):
        resolve_publisher(Platform.LINKEDIN, settings())
    assert isinstance(resolve_publisher(Platform.VK, settings(app_env="production", publishing_dry_run=True)), VkPublisher)


def test_media_path_cannot_escape_media_root(tmp_path: Path) -> None:
    class Asset:
        id = uuid.uuid4()
        file_path = "../outside.png"
        media_type = type("MediaType", (), {"value": "image"})()

    with pytest.raises(PublisherPermanentError):
        resolve_publication_media([Asset()], tmp_path)
