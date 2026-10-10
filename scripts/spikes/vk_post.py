"""Manual spike for official VK API text and optional image publication to a group."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

from _common import OUTPUT_DIR, fail, load_project_env, optional_env, required_env

API_ROOT = "https://api.vk.com/method"
TEXT_MESSAGE = "ContentPilot M0 integration test"


def vk_api(client: httpx.Client, method: str, token: str, version: str, **params: str) -> object:
    response = client.post(f"{API_ROOT}/{method}", data={"access_token": token, "v": version, **params})
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        error = body["error"]
        raise RuntimeError(f"VK API error {error.get('error_code')}: {error.get('error_msg')}")
    return body["response"]


def normalized_group_id() -> str:
    value = required_env("VK_GROUP_ID")
    try:
        group_id = abs(int(value))
    except ValueError as error:
        raise ValueError("VK_GROUP_ID must be a numeric group ID") from error
    if group_id == 0:
        raise ValueError("VK_GROUP_ID must not be zero")
    return str(group_id)


def post_text(client: httpx.Client, token: str, version: str, group_id: str) -> None:
    vk_api(client, "wall.post", token, version, owner_id=f"-{group_id}", from_group="1", message=TEXT_MESSAGE)


def user_access_token() -> str:
    configured = optional_env("VK_USER_ACCESS_TOKEN", "")
    if configured:
        return configured
    token_path = OUTPUT_DIR / "vk-user-token.json"
    if not token_path.is_file():
        raise ValueError(
            "Missing user token: set VK_USER_ACCESS_TOKEN or run `vk_oauth.py authorize` and exchange"
        )
    try:
        saved = json.loads(token_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("Local VK user token file is not valid JSON") from error
    token = saved.get("access_token") if isinstance(saved, dict) else None
    if not isinstance(token, str) or not token:
        raise ValueError("Local VK user token file does not contain access_token")
    return token


def upload_and_post_image(
    client: httpx.Client,
    community_token: str,
    user_token: str,
    version: str,
    group_id: str,
    image_path: Path,
) -> None:
    upload_server = vk_api(client, "photos.getWallUploadServer", user_token, version, group_id=group_id)
    with image_path.open("rb") as image_file:
        upload_response = client.post(upload_server["upload_url"], files={"photo": (image_path.name, image_file, "image/png")})
    if upload_response.is_error:
        raise RuntimeError(f"VK image upload HTTP error {upload_response.status_code}")
    uploaded = upload_response.json()
    saved = vk_api(
        client, "photos.saveWallPhoto", user_token, version, group_id=group_id,
        photo=uploaded["photo"], server=str(uploaded["server"]), hash=uploaded["hash"],
    )[0]
    attachment = f"photo{saved['owner_id']}_{saved['id']}"
    if saved.get("access_key"):
        attachment += f"_{saved['access_key']}"
    vk_api(client, "wall.post", community_token, version, owner_id=f"-{group_id}", from_group="1", message="ContentPilot M0 image integration test", attachments=attachment)


def main() -> None:
    load_project_env()
    try:
        community_token = required_env("VK_ACCESS_TOKEN")
        group_id = normalized_group_id()
        version = optional_env("VK_API_VERSION", "5.199")
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            vk_api(client, "groups.getById", community_token, version, group_id=group_id)
            post_text(client, community_token, version, group_id)
            print("VK TEXT: PASS")
            image_path = OUTPUT_DIR / "proxyapi-image.png"
            if not image_path.is_file():
                print("VK IMAGE: SKIPPED - generated image not found")
                return
            try:
                upload_and_post_image(
                    client,
                    community_token,
                    user_access_token(),
                    version,
                    group_id,
                    image_path,
                )
            except Exception as image_error:
                print(f"VK IMAGE: FAIL - {image_error}")
                raise SystemExit(1) from image_error
            print("VK IMAGE: PASS")
    except SystemExit:
        raise
    except Exception as error:
        fail("VK", error)


if __name__ == "__main__":
    main()
