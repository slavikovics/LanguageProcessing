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
