"""Regression coverage for Celery's import-safe bootstrap configuration."""
from __future__ import annotations

import os
import subprocess
import sys

from content_pilot.config import CeleryBootstrapSettings


def test_celery_bootstrap_uses_default_broker_without_application_secrets() -> None:
    settings = CeleryBootstrapSettings(_env_file=None)

    assert settings.resolved_broker_url == "redis://content-pilot-redis:6379/0"
    assert settings.celery_dispatch_interval_seconds == 60


def test_celery_app_imports_without_env_file_or_postgres_password(tmp_path) -> None:
    environment = os.environ.copy()
    for name in (
        "POSTGRES_PASSWORD",
        "DATABASE_URL",
        "PROXYAPI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "VK_ACCESS_TOKEN",
    ):
        environment.pop(name, None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from content_pilot.tasks.celery_app import celery_app; "
                "assert celery_app.conf.broker_url == 'redis://content-pilot-redis:6379/0'"
            ),
        ],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
