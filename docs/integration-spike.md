# ContentPilot M0 — External integration spike

This is a manual results log. Runtime scripts must not modify this file.

| Integration | Text | Image | Status | Notes |
|-------------|------|-------|--------|-------|
| ProxyAPI | TBD | TBD | TBD | |
| LinkedIn | BLOCKED | BLOCKED | BLOCKED | Page verification required |
| VK | TBD | TBD | TBD | Community token works for text; image requires PKCE user token (`photos wall`) |
| Telegram | TBD | TBD | TBD | |

## LinkedIn decision for v0.1

Automatic LinkedIn publishing is blocked because a LinkedIn Developer App cannot
currently be created: creating the required LinkedIn Page requires account
verification. ContentPilot will still generate LinkedIn-specific text and image for
manual publication in v0.1. An automatic LinkedIn publisher can be added later when
official API access becomes available. No unofficial or private API is used.

## VK token split for M0

The community access token is retained for `wall.post` text publication. The image
flow uses a short-lived user access token with `photos wall` scopes: obtain it through
the official VK ID Authorization Code + PKCE spike, then refresh it using the locally
stored refresh token and device ID. OAuth state and token files are local Git-ignored
artifacts. The scripts do not update this manual log at runtime.
