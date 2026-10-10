"""Manual VK ID OAuth Authorization Code + PKCE spike for a short-lived user token."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from _common import OUTPUT_DIR, fail, load_project_env, optional_env, required_env

AUTHORIZE_URL = "https://id.vk.com/authorize"
TOKEN_URL = "https://id.vk.com/oauth2/auth"
STATE_PATH = OUTPUT_DIR / "vk-oauth-state.json"
TOKEN_PATH = OUTPUT_DIR / "vk-user-token.json"


def write_json(path: Path, payload: dict[str, object]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, description: str) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"{description} not found: run `vk_oauth.py authorize` first")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{description} is not valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{description} has an invalid format")
    return payload


def required_value(payload: dict[str, object], name: str, description: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{description} does not contain {name}")
    return value


def pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def authorize() -> None:
    client_id = required_env("VK_CLIENT_ID")
    redirect_uri = required_env("VK_REDIRECT_URI")
    scope = optional_env("VK_OAUTH_SCOPE", "photos wall")
    code_verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(32)
    write_json(STATE_PATH, {"code_verifier": code_verifier, "state": state})
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": pkce_challenge(code_verifier),
            "code_challenge_method": "s256",
        }
    )
    print(f"Authorization URL: {AUTHORIZE_URL}?{query}")
    print("VK OAUTH AUTHORIZE: PASS")


def parse_redirect_payload(payload: str) -> dict[str, str]:
    parsed = urlparse(payload)
    query = parsed.query or parsed.fragment
    if not query:
        query = payload.lstrip("?")
    parsed_values = parse_qs(query, keep_blank_values=True)
    return {name: values[0] for name, values in parsed_values.items() if values}


def token_request(form: dict[str, str]) -> dict[str, object]:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(TOKEN_URL, data=form)
    if response.is_error:
        raise RuntimeError(f"VK ID OAuth HTTP error {response.status_code}")
    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("VK ID OAuth returned a non-JSON response") from error
    if not isinstance(payload, dict):
        raise RuntimeError("VK ID OAuth returned an unexpected response format")
    if payload.get("error"):
        raise RuntimeError(f"VK ID OAuth error: {payload.get('error_description', payload['error'])}")
    return payload


def save_token_response(response: dict[str, object], device_id: str) -> dict[str, object]:
    access_token = required_value(response, "access_token", "VK ID OAuth response")
    refresh_token = required_value(response, "refresh_token", "VK ID OAuth response")
    saved = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "device_id": str(response.get("device_id") or device_id),
        "user_id": response.get("user_id"),
        "expires_in": response.get("expires_in"),
        "scope": response.get("scope"),
    }
    write_json(TOKEN_PATH, saved)
    return saved


def exchange(payload: str) -> None:
    redirect_values = parse_redirect_payload(payload)
    code = required_value(redirect_values, "code", "Redirect payload")
    device_id = required_value(redirect_values, "device_id", "Redirect payload")
    returned_state = required_value(redirect_values, "state", "Redirect payload")
    saved_state = read_json(STATE_PATH, "OAuth state")
    expected_state = required_value(saved_state, "state", "OAuth state")
    if not secrets.compare_digest(returned_state, expected_state):
        raise ValueError("OAuth state does not match the authorization request")
    response = token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": required_value(saved_state, "code_verifier", "OAuth state"),
            "device_id": device_id,
            "client_id": required_env("VK_CLIENT_ID"),
            "redirect_uri": required_env("VK_REDIRECT_URI"),
            "state": returned_state,
        }
    )
    saved = save_token_response(response, device_id)
    print(f"user_id: {saved['user_id']}")
    print(f"expires_in: {saved['expires_in']}")
    print(f"scope: {saved['scope']}")
    print("VK OAUTH EXCHANGE: PASS")


def refresh() -> None:
    saved_token = read_json(TOKEN_PATH, "User token file")
    device_id = required_value(saved_token, "device_id", "User token file")
    response = token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": required_value(saved_token, "refresh_token", "User token file"),
            "client_id": required_env("VK_CLIENT_ID"),
            "device_id": device_id,
            "state": secrets.token_urlsafe(32),
        }
    )
    save_token_response(response, device_id)
    print("VK OAUTH REFRESH: PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("authorize", help="Print a VK ID authorization URL")
    exchange_parser = subparsers.add_parser("exchange", help="Exchange the redirect payload")
    exchange_parser.add_argument("--payload", required=True, help="Complete redirect URL or its query payload")
    subparsers.add_parser("refresh", help="Refresh the locally stored user token")
    args = parser.parse_args()
    load_project_env()
    try:
        if args.command == "authorize":
            authorize()
        elif args.command == "exchange":
            exchange(args.payload)
        else:
            refresh()
    except Exception as error:
        fail("VK OAUTH", error)


if __name__ == "__main__":
    main()
