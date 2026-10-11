# ContentPilot

ContentPilot is a modular monolith for AI-assisted content planning and future social publishing. M3 adds a server-rendered Russian Web UI, manual post editing, images, and a persisted post workflow. Automatic publishing, background scheduling execution, authentication, and analytics remain out of scope.

## Stack

- Python 3.12, FastAPI, Uvicorn, Jinja2, plain CSS and vanilla JavaScript
- PostgreSQL, SQLAlchemy 2 (synchronous), psycopg, Alembic
- Pydantic Settings and pytest
- Docker Compose; Redis is provisioned only as future infrastructure
- ProxyAPI through the OpenAI SDK, isolated behind the `content_pilot.ai` provider layer

## Project layout

```text
src/content_pilot/  FastAPI, settings, database primitives, ORM models, routes
  ai/               structured provider schemas, prompts, ProxyAPI client
  services/         plan, draft-post, media, project, dashboard, and workflow logic
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
draft -> approved -> scheduled
draft -> cancelled
approved -> cancelled
scheduled -> approved  (unschedule)
scheduled -> cancelled
```

`APP_TIMEZONE` defaults to `Europe/Samara`. The UI accepts schedule input in that IANA timezone and the workflow stores it as UTC. Scheduling in M3 only persists the time; no scheduler or external publisher runs yet.

LinkedIn is explicitly manual: the post page provides copy-text and image-preview actions, not a publish button. VK and Telegram pages likewise show no automatic publishing controls.

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
