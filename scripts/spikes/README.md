# ContentPilot M0 spikes

These are deliberately small, one-off diagnostic scripts. They are not application
code and do not create a database, web service, queue, or publisher abstraction.

## Setup

1. Copy `.env.example` to `.env` and fill only the credentials needed for the spike.
2. Install the project dependencies with Python 3.12:

   ```powershell
   python -m pip install -e .
   ```

3. Run the external checks in this order:

   ```powershell
   python scripts/spikes/proxyapi_text.py
   python scripts/spikes/proxyapi_image.py
   python scripts/spikes/telegram_post.py
   python scripts/spikes/vk_oauth.py authorize
   python scripts/spikes/vk_post.py
   ```

The image spike writes `scripts/spikes/output/proxyapi-image.png`; that directory is
ignored by Git. Telegram and VK scripts create real test publications in the
configured user-owned chat/community.

## Required settings by spike

| Spike | Required `.env` variables | Result |
| --- | --- | --- |
| `proxyapi_text.py` | `PROXYAPI_API_KEY`; optional `PROXYAPI_BASE_URL`, `PROXYAPI_TEXT_MODEL` | Generates text and prints a short preview. |
| `proxyapi_image.py` | `PROXYAPI_API_KEY`; optional `PROXYAPI_BASE_URL`, `PROXYAPI_IMAGE_MODEL` | Saves `output/proxyapi-image.png`; supports base64 and URL responses. |
| `telegram_post.py` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Calls `getMe`, sends text, then sends the image when present. |
| `vk_oauth.py authorize` | `VK_CLIENT_ID`, `VK_REDIRECT_URI`; optional `VK_OAUTH_SCOPE` | Creates PKCE state locally and prints a VK ID authorization URL without opening a browser. |
| `vk_oauth.py exchange --payload "..."` | `VK_CLIENT_ID`, `VK_REDIRECT_URI`, plus saved authorization state | Validates redirect state and saves a short-lived user token locally. |
| `vk_oauth.py refresh` | `VK_CLIENT_ID`, plus saved user token | Refreshes the local user token. |
| `vk_post.py` | `VK_ACCESS_TOKEN`, `VK_GROUP_ID`; optional `VK_API_VERSION`, `VK_USER_ACCESS_TOKEN` | Text uses the community token. Image uses a user token from `VK_USER_ACCESS_TOKEN` or local OAuth output. |

Every successful capability prints `PASS`. Configuration/API errors print `FAIL` and
exit with code 1. An image publication failure does not hide an already successful
text post, but leaves code 1 so manual validation notices it.

## VK ID OAuth for image posting

`photos.getWallUploadServer` and `photos.saveWallPhoto` require a user token with
`photos wall` scopes; the community token remains responsible for `wall.post`.
Run `python scripts/spikes/vk_oauth.py authorize`, open the printed URL manually,
then exchange the complete redirect URL (quote it because it contains `&`):

```powershell
python scripts/spikes/vk_oauth.py exchange --payload "https://example/callback?code=...&device_id=...&state=..."
```

The authorization verifier/state is stored at `output/vk-oauth-state.json`; the
short-lived access token, refresh token, and device ID are stored at
`output/vk-user-token.json`. Both are Git-ignored and tokens are never printed.
Use `python scripts/spikes/vk_oauth.py refresh` before the user access token expires.
This PKCE flow does not use a client secret.

## LinkedIn: expected blocked state

These commands intentionally exit with code 2:

```powershell
python scripts/spikes/linkedin_profile.py
python scripts/spikes/linkedin_post.py
python scripts/spikes/linkedin_image_post.py
```

They document the current blocker: a LinkedIn Developer App cannot be created because
LinkedIn Page creation requires account verification. No unofficial/private API is used.
