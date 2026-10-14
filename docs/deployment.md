# Развёртывание ContentPilot

Этот документ описывает deployment одного Docker Compose сервера. Он не
выполняет развёртывание автоматически и не содержит secrets.

## Требования сервера

- Linux-сервер с Docker Engine и Docker Compose v2;
- `curl` для финальной проверки `/health` в `scripts/deploy.sh`;
- доступ к `ghcr.io` для получения container image;
- reverse proxy, например Nginx, если интерфейс нужно открыть извне.

PostgreSQL и Redis не публикуют порты на host. API по умолчанию привязан к
`127.0.0.1:8000`; reverse proxy должен работать на том же сервере или доступ к
нему должен быть организован отдельно.

## Подготовка конфигурации

На сервере рядом с `compose.prod.yaml` создайте `.env` на основе
`.env.production.example`. Этот файл остаётся только на сервере и не должен
попадать в Git.

Обязательно задайте:

- `CONTENT_PILOT_IMAGE` — предпочтительно immutable тег вида `sha-<commit>`;
- надёжный `POSTGRES_PASSWORD`;
- `APP_ENV=production`, `APP_DEBUG=false` и `APP_TIMEZONE`;
- ключ ProxyAPI, если на сервере нужна AI-генерация;
- Telegram/VK credentials, только если нужна автоматическая публикация;
- `PUBLISHING_DRY_RUN=false` для реальных публикаций.

`content-pilot-worker` — единственный service, получающий Telegram и VK
credentials. Celery Beat не получает social secrets.

## Доступ к GHCR

Если GHCR package приватный, до первого deploy выполните на сервере:

```bash
docker login ghcr.io
```

Используйте token с правом `packages:read`. Не храните token в repository или
в `compose.prod.yaml`.

## Первый deploy и обновление

Скопируйте в deployment directory как минимум `compose.prod.yaml`,
`.env.production.example` (только как образец) и `scripts/deploy.sh`. После
подготовки server-side `.env` выполните:

```bash
CONTENT_PILOT_IMAGE=ghcr.io/<github-owner>/content-pilot:sha-<commit-sha> \
bash scripts/deploy.sh
```

Скрипт выполняет `docker compose pull`, поднимает PostgreSQL и Redis, один раз
запускает `alembic upgrade head`, затем поднимает API, worker и Celery Beat. В
конце он проверяет, что application services запущены, и ожидает успешный
`GET /health`. Перед миграцией он останавливает application services, поэтому
старый worker не обрабатывает задачи во время обновления схемы.

Watchtower намеренно не используется: обновление выполняется явно и наблюдаемо
в последовательности image pull → migration → restart → healthcheck.

Миграции не запускаются параллельно в нескольких containers. Скрипт никогда
не выполняет `alembic downgrade` и не удаляет данные.

## Диагностика

```bash
docker compose --env-file .env -f compose.prod.yaml ps
docker compose --env-file .env -f compose.prod.yaml logs -f content-pilot-api
docker compose --env-file .env -f compose.prod.yaml logs -f content-pilot-worker
curl --fail http://127.0.0.1:8000/health
```

PostgreSQL data и generated media сохраняются в named volumes. До обновлений
подготовьте и регулярно проверяйте отдельные backups PostgreSQL и media volume.
Автоматическое резервное копирование не входит в проект.

## Rollback

Для rollback укажите предыдущий immutable SHA image:

```bash
CONTENT_PILOT_IMAGE=ghcr.io/<github-owner>/content-pilot:sha-<previous-commit> \
bash scripts/deploy.sh
```

Rollback образа безопасен только при обратной совместимости application code с
уже применённой схемой базы данных. Автоматический Alembic downgrade в
production не выполняется.

## GitHub Actions deploy

Workflow `Deploy production` запускается только вручную через GitHub Actions
и использует Environment `production`. Перед его использованием настройте
environment approvals при необходимости и secrets:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_KNOWN_HOSTS`
- `DEPLOY_PORT` (необязательно; по умолчанию `22`)
- `DEPLOY_PATH`

`DEPLOY_KNOWN_HOSTS` должен содержать предварительно проверенный host key.
Workflow не отключает `StrictHostKeyChecking` и не выполняется для pull request.

## Ограничения сетевых интеграций

- Telegram API из российских сетей может требовать proxy/VPN routing;
  `TELEGRAM_PROXY_URL` пока не реализован.
- Автоматическая загрузка изображений в VK ограничена разрешением `photos`;
  ContentPilot публикует текст и оставляет изображение для ручной публикации.
- LinkedIn остаётся в manual mode.
