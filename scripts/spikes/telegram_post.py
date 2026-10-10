"""Manual spike for real Telegram Bot API text and optional image publication."""
from __future__ import annotations

from pathlib import Path

import httpx

from _common import OUTPUT_DIR, fail, load_project_env, required_env

TEXT_MESSAGE = "ContentPilot M0 integration test"


def telegram_api(client: httpx.Client, token: str, method: str, **payload: str) -> dict:
    response = client.post(f"https://api.telegram.org/bot{token}/{method}", json=payload)
    if response.is_error:
        raise RuntimeError(f"Telegram HTTP error {response.status_code}")
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(body.get("description", "Telegram API returned ok=false"))
    return body


def send_photo(client: httpx.Client, token: str, chat_id: str, image_path: Path) -> None:
    with image_path.open("rb") as image_file:
        response = client.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id, "caption": "ContentPilot M0 image integration test"},
            files={"photo": (image_path.name, image_file, "image/png")},
        )
    if response.is_error:
        raise RuntimeError(f"Telegram HTTP error {response.status_code}")
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(body.get("description", "Telegram API returned ok=false"))


def main() -> None:
    load_project_env()
    try:
        token = required_env("TELEGRAM_BOT_TOKEN")
        chat_id = required_env("TELEGRAM_CHAT_ID")
        with httpx.Client(timeout=30.0) as client:
            telegram_api(client, token, "getMe")
            telegram_api(client, token, "sendMessage", chat_id=chat_id, text=TEXT_MESSAGE)
            print("TELEGRAM TEXT: PASS")
            image_path = OUTPUT_DIR / "proxyapi-image.png"
            if not image_path.is_file():
                print("TELEGRAM IMAGE: SKIPPED - generated image not found")
                return
            try:
                send_photo(client, token, chat_id, image_path)
            except Exception as image_error:
                print(f"TELEGRAM IMAGE: FAIL - {image_error}")
                raise SystemExit(1) from image_error
            print("TELEGRAM IMAGE: PASS")
    except SystemExit:
        raise
    except Exception as error:
        fail("TELEGRAM", error)


if __name__ == "__main__":
    main()
