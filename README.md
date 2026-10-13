# ContentPilot

ContentPilot 0.1.0 is a single-user MVP for AI-assisted content planning,
platform-specific drafting, image generation, scheduling, and social publishing.
The server-rendered interface is Russian-first and is designed for a practical
developer personal-brand workflow.

## Features

- Structured AI content plans and platform-specific posts through ProxyAPI
- AI image generation stored under `MEDIA_ROOT`
- Draft, approval, scheduling, cancellation, and publication workflow
- PostgreSQL-backed scheduling with Celery Beat, Redis, and a low-concurrency worker
- Telegram automatic text and image publication
- VK community automatic text publication
- LinkedIn manual copy/download workflow
- Internal publication analytics and attempt history

## Architecture

```text
Browser
  ↓
FastAPI + Jinja2
  ↓
PostgreSQL

AI generation → ProxyAPI

Celery Beat
  ↓
Redis
  ↓
Celery Worker
  ↓
Telegram / VK
  ↓
PostgreSQL
```

PostgreSQL is the source of truth for schedules, post state, and publication
attempts. Redis is Celery's broker only.

## Tech stack

- Python 3.12, FastAPI, Uvicorn, Jinja2, vanilla CSS/JavaScript
- PostgreSQL, SQLAlchemy 2, Alembic, psycopg
- Pydantic Settings, httpx, OpenAI SDK, ProxyAPI
- Redis, Celery Worker, Celery Beat
- pytest and Docker Compose

## Platform capabilities

| Platform | Text generation | Image generation | Auto text publish | Auto image publish |
|---|---:|---:|---:|---:|
| LinkedIn | yes | yes | no, manual | no, manual |
| VK | yes | yes | yes | no, manual fallback |
| Telegram | yes | yes | yes | yes |

## Local setup

Use Python 3.12 and Docker Desktop.

```powershell
Copy-Item .env.example .env
python -m pip install -e ".[dev]"
python -m pytest -q
docker compose up -d --build
docker compose exec content-pilot-api alembic upgrade head
```

Open `http://localhost:8002/`. Main routes are `/`, `/projects`, `/health`, and
`/api/health`.

## Environment variables

Set a strong `POSTGRES_PASSWORD`; `.env` is Git-ignored. `PROXYAPI_API_KEY` is
required only for AI generation. Social credentials are deliberately environment
based for this single-user MVP and are supplied only to the worker container.

```dotenv
# Publishing
PUBLISHING_DRY_RUN=false
SOCIAL_HTTP_TIMEOUT_SECONDS=30

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# VK community
VK_ACCESS_TOKEN=
VK_GROUP_ID=
VK_API_VERSION=5.199
```

For safe scheduler tests, use `APP_ENV=development` and
`PUBLISHING_DRY_RUN=true`. This selects `DryRunPublisher` and sends no HTTP
requests.

## Database migrations

```powershell
docker compose exec content-pilot-api alembic current
docker compose exec content-pilot-api alembic upgrade head
docker compose exec content-pilot-api alembic check
```

Tables are managed only by Alembic; application startup does not call
`Base.metadata.create_all()`.

## Celery and scheduling

Beat periodically queues UUIDs for due scheduled posts. The worker atomically
claims a row as `publishing`, creates `PublicationAttempt`, invokes a publisher
outside the database transaction, then persists `published` or `failed`.
Default worker concurrency is `1`.

```powershell
docker compose logs -f content-pilot-beat
docker compose logs -f content-pilot-worker
```

## Social integration setup

Telegram uses the official Bot API. For image posts within Telegram's caption
limit, text is sent as a caption. Longer posts are sent as an image message and
a separate full-text message, without truncation.

VK uses the official community `wall.post` method. If a post has generated
media, ContentPilot still publishes text and leaves the image available for
manual publishing. It intentionally does not call
[`photos.getWallUploadServer`](https://dev.vk.ru/ru/method/photos.getWallUploadServer):
the required user `photos` permission is restricted for new applications and
would need a future request to `devsupport@corp.vk.com`.

## Known limitations

- LinkedIn official API access is blocked by Page/account verification; it is manual-only.
- VK automatic image upload is intentionally unavailable for the permission reason above.
- Telegram API networking from Russian networks may require proxy/VPN routing. A future
  `TELEGRAM_PROXY_URL` could be isolated inside TelegramPublisher; it is not active now.
- Publication is at-least-once at the external boundary: a provider success followed by
  worker/database failure can result in a duplicate during retry.
- There is no auth, multi-user credential storage, social engagement analytics, or CI/CD.

## Demo and release preparation

Use the project **«Личный бренд Python-разработчика»** with Russian language,
professional practical tone, and a Python-backend/AI-automation audience.
Detailed screenshot, screencast, and Zerocoder-delivery steps are in
[`docs/release-checklist.md`](docs/release-checklist.md). The future DOCX source
outline is [`docs/spec-outline.md`](docs/spec-outline.md).

## Screenshots

- Dashboard
- Content plan
- Post editor and image
- Scheduling
- Publication history

## M0 spikes

[`scripts/spikes/README.md`](scripts/spikes/README.md) contains independent,
manual external-integration diagnostics. They are never run by pytest or normal
application startup; Telegram and VK spike commands can create real posts.
