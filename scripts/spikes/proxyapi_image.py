"""Manual connectivity spike for ProxyAPI image generation through the OpenAI SDK."""
from __future__ import annotations

import base64
from pathlib import Path

import httpx
from openai import OpenAI

from _common import OUTPUT_DIR, fail, load_project_env, optional_env, required_env

PROMPT = "Minimal professional illustration for a social media post about Python backend development, dark clean technology aesthetic, no text"


def image_bytes_from_response() -> bytes:
    client = OpenAI(api_key=required_env("PROXYAPI_API_KEY"), base_url=optional_env("PROXYAPI_BASE_URL", "https://api.proxyapi.ru/v1"))
    response = client.images.generate(model=optional_env("PROXYAPI_IMAGE_MODEL", "openai/gpt-image-1-mini"), prompt=PROMPT, size="1024x1024")
    image = response.data[0]
    if image.b64_json:
        return base64.b64decode(image.b64_json, validate=True)
    if image.url:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            downloaded = client.get(image.url)
            if downloaded.is_error:
                raise RuntimeError(f"Image download HTTP error {downloaded.status_code}")
            return downloaded.content
    raise RuntimeError("API response contained neither base64 image data nor an image URL")


def save_image(data: bytes) -> Path:
    if not data:
        raise RuntimeError("Generated image data is empty")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / "proxyapi-image.png"
    destination.write_bytes(data)
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("Image file was not saved or is empty")
    return destination


def main() -> None:
    load_project_env()
    try:
        destination = save_image(image_bytes_from_response())
    except Exception as error:
        fail("PROXYAPI IMAGE", error)
    print(f"Saved image: {destination}")
    print("PROXYAPI IMAGE: PASS")


if __name__ == "__main__":
    main()
