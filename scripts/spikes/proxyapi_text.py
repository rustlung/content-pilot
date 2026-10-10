"""Manual connectivity spike for ProxyAPI text generation through the OpenAI SDK."""
from __future__ import annotations

from openai import OpenAI

from _common import fail, load_project_env, optional_env, preview, required_env

PROMPT = "Напиши короткий профессиональный пост для LinkedIn о разработке Python backend. Не более 500 символов."


def generate_text() -> str:
    client = OpenAI(api_key=required_env("PROXYAPI_API_KEY"), base_url=optional_env("PROXYAPI_BASE_URL", "https://api.proxyapi.ru/v1"))
    response = client.chat.completions.create(
        model=optional_env("PROXYAPI_TEXT_MODEL", "openai/gpt-4.1-mini"),
        messages=[{"role": "user", "content": PROMPT}],
    )
    text = response.choices[0].message.content or ""
    if not text.strip():
        raise RuntimeError("API returned an empty text response")
    return text


def main() -> None:
    load_project_env()
    try:
        text = generate_text()
    except Exception as error:
        fail("PROXYAPI TEXT", error)
    print(f"Preview: {preview(text)}")
    print("PROXYAPI TEXT: PASS")


if __name__ == "__main__":
    main()
