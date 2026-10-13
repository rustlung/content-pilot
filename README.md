# ContentPilot

ContentPilot 0.1.0 — однопользовательский MVP для AI-ассистированного
контент-планирования, подготовки версий постов для разных платформ, генерации
изображений, планирования публикаций и публикации в соцсетях. Серверный
интерфейс ориентирован прежде всего на русский язык и практический процесс
личного бренда разработчика.

## Возможности

- Структурированные AI-контент-планы и посты для платформ через ProxyAPI
- Генерация AI-изображений с хранением в `MEDIA_ROOT`
- Процесс: черновик, подтверждение, планирование, отмена и публикация
- Планирование на базе PostgreSQL с Celery Beat, Redis и worker с ограниченной concurrency
- Автоматическая публикация текста и изображений в Telegram
- Автоматическая публикация текста в VK-сообществе
- Ручной процесс копирования и скачивания для LinkedIn
- Внутренняя аналитика публикаций и история попыток

## Архитектура

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

PostgreSQL — источник истины для расписания, состояния постов и попыток
публикации. Redis используется только как брокер Celery.

## Технологический стек

- Python 3.12, FastAPI, Uvicorn, Jinja2, vanilla CSS/JavaScript
- PostgreSQL, SQLAlchemy 2, Alembic, psycopg
- Pydantic Settings, httpx, OpenAI SDK, ProxyAPI
- Redis, Celery Worker, Celery Beat
- pytest и Docker Compose

## Возможности платформ

| Платформа | Генерация текста | Генерация изображения | Автопубликация текста | Автопубликация изображения |
|---|---:|---:|---:|---:|
| LinkedIn | да | да | нет, вручную | нет, вручную |
| VK | да | да | да | нет, вручную |
| Telegram | да | да | да | да |

## Локальный запуск

Используйте Python 3.12 и Docker Desktop.

```powershell
Copy-Item .env.example .env
python -m pip install -e ".[dev]"
python -m pytest -q
docker compose up -d --build
docker compose exec content-pilot-api alembic upgrade head
```

Откройте `http://localhost:8002/`. Основные маршруты: `/`, `/projects`,
`/health` и `/api/health`.

## Переменные окружения

Укажите надёжный `POSTGRES_PASSWORD`; `.env` игнорируется Git. `PROXYAPI_API_KEY`
нужен только для AI-генерации. Учётные данные соцсетей намеренно хранятся в
переменных окружения для этого однопользовательского MVP и передаются только в
контейнер worker.

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

Для безопасной проверки scheduler используйте `APP_ENV=development` и
`PUBLISHING_DRY_RUN=true`. Будет выбран `DryRunPublisher`, который не выполняет
HTTP-запросов.

## Миграции базы данных

```powershell
docker compose exec content-pilot-api alembic current
docker compose exec content-pilot-api alembic upgrade head
docker compose exec content-pilot-api alembic check
```

Таблицами управляет только Alembic; при старте приложения не вызывается
`Base.metadata.create_all()`.

## Celery и планирование публикаций

Celery Beat периодически ставит UUID наступивших запланированных постов в
очередь. Worker атомарно переводит запись в `publishing`, создаёт
`PublicationAttempt`, вызывает адаптер публикации вне транзакции базы данных,
после чего сохраняет `published` или `failed`. Значение worker concurrency по
умолчанию — `1`.

```powershell
docker compose logs -f content-pilot-beat
docker compose logs -f content-pilot-worker
```

## Настройка социальных интеграций

Telegram использует официальный Bot API. Для постов с изображением, если текст
укладывается в лимит caption Telegram, он отправляется в caption. Более длинные
посты отправляются отдельным сообщением с изображением и отдельным полным
текстом без обрезания.

VK использует официальный метод сообщества `wall.post`. Если у поста есть
сгенерированное медиа, ContentPilot всё равно публикует текст и оставляет
изображение доступным для ручной публикации. Приложение намеренно не вызывает
[`photos.getWallUploadServer`](https://dev.vk.ru/ru/method/photos.getWallUploadServer):
требуемое пользовательское разрешение `photos` ограничено для новых приложений
и в будущем потребует обращения в `devsupport@corp.vk.com`.

## Известные ограничения

- Доступ к официальному API LinkedIn заблокирован проверкой Page/аккаунта;
  доступна только ручная публикация.
- Автоматическая загрузка изображений в VK намеренно недоступна по указанной
  выше причине, связанной с разрешениями.
- Для доступа к Telegram API из российских сетей может потребоваться proxy/VPN.
  Будущий `TELEGRAM_PROXY_URL` можно изолировать внутри TelegramPublisher; сейчас
  он не используется.
- На внешней границе публикация имеет семантику at-least-once: успешный ответ
  провайдера перед сбоем worker/базы данных может привести к дублированию при retry.
- Нет auth, хранения credentials для нескольких пользователей, аналитики вовлечённости
  в соцсетях и CI/CD.

## Демо и подготовка к релизу

Используйте проект **«Личный бренд Python-разработчика»** с русским языком,
профессиональным практичным тоном и аудиторией, связанной с Python backend и
AI-автоматизацией. Подробный план создания скриншотов, скринкаста и сдачи
Zerocoder находится в [`docs/release-checklist.md`](docs/release-checklist.md).
Исходный план для будущего DOCX —
[`docs/spec-outline.md`](docs/spec-outline.md).

## Скриншоты

- Дашборд
- Контент-план
- Редактор поста и изображение
- Планирование публикации
- История публикации

## M0-спайки

[`scripts/spikes/README.md`](scripts/spikes/README.md) содержит независимые
ручные диагностические скрипты внешних интеграций. Они никогда не запускаются
через pytest или при обычном старте приложения; команды спайков Telegram и VK
могут создать реальные публикации.
