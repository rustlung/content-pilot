"""Regression coverage for Celery's import-safe bootstrap configuration."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from content_pilot.ai.client import AIClient, AIConfigurationError
from content_pilot.config import AISettings, CeleryBootstrapSettings, PublicationSettings


def test_celery_bootstrap_uses_default_broker_without_application_secrets() -> None:
    settings = CeleryBootstrapSettings(_env_file=None)

    assert settings.resolved_broker_url == "redis://content-pilot-redis:6379/0"
    assert settings.celery_dispatch_interval_seconds == 60


def test_publication_settings_do_not_require_database_credentials() -> None:
    settings = PublicationSettings(_env_file=None)

    assert settings.publication_max_retries == 3
    assert settings.media_root.name == "media"


def test_ai_settings_do_not_require_database_credentials_or_api_key() -> None:
    settings = AISettings(_env_file=None)

    assert settings.proxyapi_api_key is None
    assert settings.ai_timeout_seconds == 60
    with pytest.raises(AIConfigurationError):
        AIClient(settings)._client()


def test_runtime_modules_import_without_env_file_or_runtime_secrets(tmp_path) -> None:
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
                "import content_pilot.tasks.publishing; "
                "import content_pilot.tasks.scheduling; "
                "import content_pilot.publishers.registry; "
                "import content_pilot.publishers.telegram; "
                "import content_pilot.publishers.vk; "
                "import content_pilot.ai.client; "
                "from content_pilot.api.dependencies import get_ai_provider; "
                "from content_pilot.app import create_app; "
                "assert get_ai_provider().settings.proxyapi_api_key is None; "
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
