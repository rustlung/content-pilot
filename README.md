# ContentPilot

ContentPilot is a modular monolith for AI-assisted content planning and future social publishing. M4 adds Redis-backed Celery scheduling and a safe DryRunPublisher pipeline; real social-network publishers remain out of scope.

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

## M4 scheduling

PostgreSQL remains the source of truth for `scheduled_at`, status, and publication attempts. Beat periodically places only due post identifiers on Redis; a worker atomically claims a row before it invokes a publisher. This avoids relying on Celery ETA messages for schedules and lets Beat rediscover overdue posts after a restart.

```text
FastAPI -> PostgreSQL

Celery Beat -> Redis -> Celery Worker -> Publisher -> PostgreSQL
```

The worker runs with `CELERY_WORKER_CONCURRENCY=1` by default. `CELERY_DISPATCH_INTERVAL_SECONDS`, `PUBLICATION_MAX_RETRIES`, and `PUBLICATION_RETRY_BASE_SECONDS` are configured in `.env`. Retryable provider failures use exponential backoff; task results are not stored in Redis because lifecycle state is persisted in PostgreSQL.

No real publisher exists in M4. For the deliberate local acceptance scenario only, set `APP_ENV=development` and `PUBLISHING_DRY_RUN=true`; `DryRunPublisher` then returns a `dry-run:<uuid>` external ID without making HTTP requests. With dry-run disabled, a scheduled VK/Telegram post safely becomes `failed` with a publisher-unavailable error. M5 will provide real adapters.

```powershell
docker compose up -d --build
docker compose exec content-pilot-api alembic upgrade head
docker compose logs -f content-pilot-beat
docker compose logs -f content-pilot-worker
```

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
