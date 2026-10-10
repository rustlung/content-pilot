FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "content_pilot.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
