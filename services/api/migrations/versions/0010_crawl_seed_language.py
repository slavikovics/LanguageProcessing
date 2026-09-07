"""Per-seed crawl language: each crawl_seed (and the crawl_job it spawns)
now carries its own `language`, replacing the one-language-per-collection
assumption — a collection can now mix seeds (e.g. en.wikipedia.org and
fr.wikipedia.org feeding the same collection), each stamping its own
documents with the right `Document.language` hint.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crawl_seeds", sa.Column("language", sa.String(10), nullable=False, server_default="en")
    )
    op.add_column(
        "crawl_jobs", sa.Column("language", sa.String(10), nullable=False, server_default="en")
    )


def downgrade() -> None:
    op.drop_column("crawl_jobs", "language")
    op.drop_column("crawl_seeds", "language")
