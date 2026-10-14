FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system contentpilot \
    && adduser --system --ingroup contentpilot --home /app contentpilot

COPY pyproject.toml /app/
COPY src /app/src
COPY alembic.ini /app/
COPY alembic /app/alembic
RUN pip install . \
    && mkdir -p /app/data/media \
    && chown -R contentpilot:contentpilot /app

USER contentpilot

EXPOSE 8000

CMD ["uvicorn", "content_pilot.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
