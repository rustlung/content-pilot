# ContentPilot

ContentPilot is a modular-monolith foundation for content planning and eventual social publishing. M1 establishes the application shell, PostgreSQL schema, and migration workflow. AI generation, background tasks, publishers, authentication, and the M3 interface are intentionally out of scope.

## Stack

- Python 3.12, FastAPI, Uvicorn, Jinja2
- PostgreSQL, SQLAlchemy 2 (synchronous), psycopg, Alembic
- Pydantic Settings and pytest
- Docker Compose; Redis is provisioned only as future infrastructure

## Project layout

```text
src/content_pilot/  FastAPI, settings, database primitives, ORM models, routes
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

The Compose starter endpoints are `http://localhost:8001/`, `/health`, and `/api/health`.

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
