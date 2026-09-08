from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crawl_seeds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("max_documents", sa.Integer(), nullable=False),
        sa.Column("max_depth", sa.Integer(), nullable=False),
        sa.Column("same_domain_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("collection_id", "url", name="uq_crawl_seed_collection_url"),
    )
    op.create_index("ix_crawl_seeds_collection_id", "crawl_seeds", ["collection_id"])

    op.add_column(
        "crawl_jobs",
        sa.Column("allowed_domain", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crawl_jobs", "allowed_domain")
    op.drop_index("ix_crawl_seeds_collection_id", table_name="crawl_seeds")
    op.drop_table("crawl_seeds")
