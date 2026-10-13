"""Celery configuration; Redis is broker only, PostgreSQL remains state storage."""
from celery import Celery

from content_pilot.config import Settings

settings = Settings()
celery_app = Celery("content_pilot", broker=settings.resolved_celery_broker_url, include=["content_pilot.tasks.scheduling", "content_pilot.tasks.publishing"])
celery_app.conf.update(task_serializer="json", accept_content=["json"], enable_utc=True, timezone="UTC", task_ignore_result=True)
celery_app.conf.beat_schedule = {
    "dispatch-due-posts": {"task": "content_pilot.dispatch_due_posts", "schedule": settings.celery_dispatch_interval_seconds}
}
