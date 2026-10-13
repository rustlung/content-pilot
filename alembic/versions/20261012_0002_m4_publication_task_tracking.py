"""Add Celery ownership tracking to publication attempts.

Revision ID: 20261012_0002
Revises: 20261010_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20261012_0002"
down_revision = "20261010_0001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("publication_attempts", sa.Column("celery_task_id", sa.String(length=255), nullable=True))
    op.create_index("ix_publication_attempts_celery_task_id", "publication_attempts", ["celery_task_id"])

def downgrade() -> None:
    op.drop_index("ix_publication_attempts_celery_task_id", table_name="publication_attempts")
    op.drop_column("publication_attempts", "celery_task_id")
