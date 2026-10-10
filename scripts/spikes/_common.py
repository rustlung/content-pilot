"""Small shared utilities for manually-run M0 integration spikes."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "spikes" / "output"


def load_project_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def optional_env(name: str, default: str) -> str:
    return os.getenv(name, "").strip() or default


def fail(integration: str, reason: Exception | str) -> None:
    print(f"{integration}: FAIL - {reason}")
    raise SystemExit(1)


def preview(text: str, limit: int = 500) -> str:
    compact = " ".join(text.split())
    return compact[:limit] + ("..." if len(compact) > limit else "")
