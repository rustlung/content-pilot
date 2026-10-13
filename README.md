# ContentPilot

ContentPilot is a modular monolith for AI-assisted content planning and social publishing. M5 adds official Telegram and VK publication adapters to the existing Celery pipeline.

## Stack

- Python 3.12, FastAPI, Uvicorn, Jinja2, plain CSS and vanilla JavaScript
- PostgreSQL, SQLAlchemy 2 (synchronous), psycopg, Alembic
- Pydantic Settings and pytest
- Docker Compose, Redis as the Celery broker, Celery worker and Celery Beat
- ProxyAPI through the OpenAI SDK, isolated behind the `content_pilot.ai` provider layer

## Project layout

```text
src/content_pilot/  FastAPI, settings, database primitives, ORM models, routes
  ai/               structured provider schemas, prompts, ProxyAPI client
  services/         plan, draft-post, media, project, dashboard, workflow, and publication persistence
  tasks/            Celery app, due-post dispatcher, and publication task
  publishers/       Telegram, VK, media-path validation, and publisher registry
  web/              server-rendered M3 pages, CSS, and small UX scripts
alembic/            schema migrations
tests/              database-free unit and metadata tests
scripts/spikes/     independent M0 external integration diagnostics
```

## Prerequisites and setup

Use Python 3.12 and Docker Desktop. Copy `.env.example` to `.env`, set a strong `POSTGRES_PASSWORD`, and retain only the M0 external credentials you need. `.env` is ignored by Git.

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
docker compose up -d --build
docker compose exec content-pilot-api alembic upgrade head
```

The Compose starter endpoints are `http://localhost:8002/`, `/projects`, `/health`, and `/api/health`.

## M3 Web UI and workflow

The UI is Russian and is served entirely by FastAPI. Use the dashboard to create a project, generate a content plan, generate a platform post, edit its draft, generate an image, and prepare it for later publication.

```text
GET  /                         dashboard
GET  /projects                 project list
GET  /projects/new             create-project form
GET  /projects/{id}            project overview
GET  /projects/{id}/plan       plan and generation form
GET  /posts/{id}               post editor and workflow actions
```

Post transitions available in M3 are:

```text
draft -> approved -> scheduled -> publishing -> published / failed
draft -> cancelled
approved -> cancelled
scheduled -> approved  (unschedule)
scheduled -> cancelled
```

`APP_TIMEZONE` defaults to `Europe/Samara`. The UI accepts schedule input in that IANA timezone and the workflow stores it as UTC. LinkedIn remains manual-only, so it cannot be scheduled for automatic publication.

LinkedIn is explicitly manual: the post page provides copy-text and image-preview actions, not a publish button. VK and Telegram pages likewise show no direct publish buttons.

## Scheduling and publishing

PostgreSQL remains the source of truth for `scheduled_at`, status, and publication attempts. Beat periodically places only due post identifiers on Redis; a worker atomically claims a row before it invokes a publisher. This avoids relying on Celery ETA messages for schedules and lets Beat rediscover overdue posts after a restart.

```text
FastAPI -> PostgreSQL

Celery Beat -> Redis -> Celery Worker -> Publisher -> PostgreSQL
```

The worker runs with `CELERY_WORKER_CONCURRENCY=1` by default. `CELERY_DISPATCH_INTERVAL_SECONDS`, `PUBLICATION_MAX_RETRIES`, and `PUBLICATION_RETRY_BASE_SECONDS` are configured in `.env`. Retryable provider failures use exponential backoff; task results are not stored in Redis because lifecycle state is persisted in PostgreSQL.

For a safe local acceptance scenario, set `APP_ENV=development` and `PUBLISHING_DRY_RUN=true`; `DryRunPublisher` then returns a `dry-run:<uuid>` external ID without making HTTP requests. In M5, setting it to `false` selects a real Telegram or VK adapter. LinkedIn remains manual-only.

```powershell
docker compose up -d --build
docker compose exec content-pilot-api alembic upgrade head
docker compose logs -f content-pilot-beat
docker compose logs -f content-pilot-worker
```

## M5 platform capabilities

| Platform | Generate text | Generate image | Auto text publish | Auto image publish |
|---|---:|---:|---:|---:|
| LinkedIn | yes | yes | no, manual | no, manual |
| VK | yes | yes | yes | no, manual fallback |
| Telegram | yes | yes | yes | yes |

Telegram uses the official Bot API. A short image post is sent with a caption; when the post exceeds Telegram's caption limit, ContentPilot sends the image and then the full text as a second message without truncating it. The persisted external ID identifies one message or, for the two-message flow, both message IDs.

VK uses the official `wall.post` community method with the configured community token. If a VK post has generated media, ContentPilot still publishes its text and keeps the image available in the UI for manual publication. It deliberately does not call `photos.getWallUploadServer`: that flow requires a user token with `photos` permission, which is restricted for new VK apps. See [VK photos.getWallUploadServer](https://dev.vk.ru/ru/method/photos.getWallUploadServer); obtaining that permission is a future support request to `devsupport@corp.vk.com`.

Configure only the worker with the relevant credentials in `.env`; Beat does not receive social tokens.

```dotenv
PUBLISHING_DRY_RUN=false
SOCIAL_HTTP_TIMEOUT_SECONDS=30

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

VK_ACCESS_TOKEN=
VK_GROUP_ID=
VK_API_VERSION=5.199
```

The M4 atomic claim protects against duplicate queued tasks, but publication is not exactly-once: if a provider accepts a post and the worker dies before PostgreSQL records success, a later retry can create a duplicate provider post. M5 intentionally does not claim a provider idempotency guarantee that has not been implemented.

## M2 AI configuration and JSON API

`PROXYAPI_API_KEY` is required only by generation endpoints; health checks and database endpoints start without it. Configure `PROXYAPI_BASE_URL`, `AI_TEXT_MODEL`, `AI_IMAGE_MODEL`, `AI_TIMEOUT_SECONDS`, and `MEDIA_ROOT` in `.env`. Generated files are stored outside the source tree under `MEDIA_ROOT`; Compose mounts it at `/app/data/media`.

```text
POST /api/projects
POST /api/projects/{project_id}/content-plan/generate
POST /api/content-items/{content_item_id}/posts/generate
POST /api/posts/{post_id}/image/generate
GET  /api/posts/{post_id}/media
```

LinkedIn generation is for manual publication only. M0 retains separate manual VK and Telegram publishing spikes; M2 sends no social-network publications.

## Manual real-provider smoke

After `alembic upgrade head` and intentional ProxyAPI configuration, run explicitly:

```powershell
docker compose exec content-pilot-api python scripts/smoke/m2_ai_smoke.py
```

It creates a small database project, three plan items, one LinkedIn draft, and one local image. It is not executed by pytest or Compose startup.

## Migrations

Run Alembic in the API container so its configured PostgreSQL host is reachable:

```powershell
docker compose exec content-pilot-api alembic current
docker compose exec content-pilot-api alembic upgrade head
docker compose exec content-pilot-api alembic check
docker compose exec content-pilot-api alembic downgrade base
docker compose exec content-pilot-api alembic upgrade head
```

Tables are managed exclusively by Alembic; the application does not call `Base.metadata.create_all()` at startup.

## M0 external spikes

The manually-run M0 diagnostics remain independent at [`scripts/spikes/README.md`](scripts/spikes/README.md). They are not executed by pytest, Docker Compose, or application startup. Telegram and VK spike commands can create real external posts, so run them only deliberately.
