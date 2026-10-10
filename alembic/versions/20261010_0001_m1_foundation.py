"""Create ContentPilot M1 foundation schema.

Revision ID: 20261010_0001
Revises:
Create Date: 2026-10-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261010_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


platform = sa.Enum("linkedin", "vk", "telegram", name="platform", native_enum=False, create_constraint=True)
content_item_status = sa.Enum(
    "draft", "planned", "cancelled", name="content_item_status", native_enum=False, create_constraint=True
)
post_status = sa.Enum(
    "draft", "approved", "scheduled", "publishing", "published", "failed", "cancelled",
    name="post_status", native_enum=False, create_constraint=True,
)
media_type = sa.Enum("image", name="media_type", native_enum=False, create_constraint=True)
media_source = sa.Enum("ai", "manual", name="media_source", native_enum=False, create_constraint=True)
publication_attempt_status = sa.Enum(
    "started", "success", "failed", name="publication_attempt_status", native_enum=False, create_constraint=True
)


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
        sa.Column("tone_of_voice", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_projects_name_not_blank"),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
    )
    op.create_table(
        "social_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("platform", platform, nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_social_accounts_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_social_accounts"),
    )
    op.create_table(
        "content_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("goal", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("status", content_item_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_content_items_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_content_items"),
    )
    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), nullable=False),
        sa.Column("platform", platform, nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("status", post_status, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_post_id", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"], name="fk_posts_content_item_id_content_items", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_posts"),
        sa.UniqueConstraint("content_item_id", "platform", name="content_item_platform"),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", media_type, nullable=False),
        sa.Column("source", media_source, nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], name="fk_media_assets_post_id_posts", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_media_assets"),
    )
    op.create_table(
        "publication_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", publication_attempt_status, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("external_response_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_no > 0", name="ck_publication_attempts_attempt_no_positive"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], name="fk_publication_attempts_post_id_posts", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_publication_attempts"),
        sa.UniqueConstraint("post_id", "attempt_no", name="post_attempt_no"),
    )


def downgrade() -> None:
    op.drop_table("publication_attempts")
    op.drop_table("media_assets")
    op.drop_table("posts")
    op.drop_table("content_items")
    op.drop_table("social_accounts")
    op.drop_table("projects")
