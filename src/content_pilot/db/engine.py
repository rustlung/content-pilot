"""Synchronous SQLAlchemy engine construction."""
from __future__ import annotations

from sqlalchemy import Engine, create_engine

from content_pilot.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
