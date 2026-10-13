# ContentPilot — specification outline

## Project

ContentPilot is a single-user MVP for AI-assisted content planning, drafting,
media generation, scheduling, and selected social publication.

## Target audience and problems

The product targets independent Python/backend specialists and small teams that
need a practical content workflow without manually coordinating plan items,
platform-specific drafts, images, and scheduled publication.

## Functional requirements

- Create and inspect projects with language, audience, and tone settings.
- Generate structured content plans and platform-specific draft posts.
- Generate local AI image assets.
- Edit, approve, schedule, cancel, and inspect posts.
- Dispatch due VK and Telegram posts through Celery.
- Persist publication attempts, safe errors, and provider external IDs.
- Display internal workflow and publication analytics.

## Non-functional requirements

- Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, Redis, and Celery.
- PostgreSQL is the source of truth; Redis is a broker only.
- Secrets stay in environment configuration and are not stored in the database.
- No real social calls run in automated tests.
- Generated media paths remain constrained to `MEDIA_ROOT`.

## Architecture

Browser → FastAPI + Jinja2 → PostgreSQL

ProxyAPI provides AI generation. Celery Beat finds due posts, Redis transports
task identifiers, and Celery Worker invokes official Telegram or VK adapters.
Publication state and attempts are persisted back to PostgreSQL.

## Platform limitations and risks

- LinkedIn is manual-only because official access is unavailable.
- VK image upload is not automated: `photos` permission is restricted for new apps.
- Telegram connectivity from Russian networks may require future proxy/VPN routing.
- Provider success followed by worker/database failure has an at-least-once duplicate edge case.
- The MVP is single-user and has no authentication or multi-user credentials.

## Deployment assumptions

Docker Compose runs API, PostgreSQL, Redis, Celery Worker, and Celery Beat on a
single host. M7 will cover CI/CD and deployment automation separately.
