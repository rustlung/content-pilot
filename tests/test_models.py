"""Metadata-only checks for the M1 foundation schema."""
from sqlalchemy import CheckConstraint, UniqueConstraint

from content_pilot.db.base import Base
import content_pilot.models  # noqa: F401 - register all models
from content_pilot.models.enums import ContentItemStatus, MediaSource, MediaType, Platform, PostStatus, PublicationAttemptStatus


def test_foundation_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {"projects", "social_accounts", "content_items", "posts", "media_assets", "publication_attempts"}


def test_enums_have_expected_values() -> None:
    assert [item.value for item in Platform] == ["linkedin", "vk", "telegram"]
    assert [item.value for item in ContentItemStatus] == ["draft", "planned", "cancelled"]
    assert [item.value for item in PostStatus] == ["draft", "approved", "scheduled", "publishing", "published", "failed", "cancelled"]
    assert [item.value for item in MediaType] == ["image"]
    assert [item.value for item in MediaSource] == ["ai", "manual"]
    assert [item.value for item in PublicationAttemptStatus] == ["started", "success", "failed"]


def test_important_constraints_and_cascades() -> None:
    posts = Base.metadata.tables["posts"]
    attempts = Base.metadata.tables["publication_attempts"]
    project = Base.metadata.tables["projects"]
    assert any(isinstance(item, UniqueConstraint) and tuple(column.name for column in item.columns) == ("content_item_id", "platform") for item in posts.constraints)
    assert any(isinstance(item, UniqueConstraint) and tuple(column.name for column in item.columns) == ("post_id", "attempt_no") for item in attempts.constraints)
    assert any(isinstance(item, CheckConstraint) for item in project.constraints)
    assert all(foreign_key.ondelete == "CASCADE" for table_name in {"social_accounts", "content_items", "posts", "media_assets", "publication_attempts"} for foreign_key in Base.metadata.tables[table_name].foreign_keys)
