"""Nullable document URLs (manually authored documents may have no source),
staleness tracking on collections (documents_changed_at), and a 'refresh'
mode for crawl_jobs that re-fetches existing URLs in place instead of
discovering new ones.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("documents", "url", existing_type=sa.String(2000), nullable=True)
    op.add_column(
        "collections",
        sa.Column("documents_changed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "crawl_jobs",
        sa.Column("mode", sa.String(20), nullable=False, server_default="crawl"),
    )


def downgrade() -> None:
    op.drop_column("crawl_jobs", "mode")
    op.drop_column("collections", "documents_changed_at")
    op.alter_column("documents", "url", existing_type=sa.String(2000), nullable=False)
