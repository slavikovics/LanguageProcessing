from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "translation_runs",
        sa.Column("method", sa.String(20), nullable=False, server_default="direct"),
    )
    op.add_column(
        "translation_test_runs",
        sa.Column("method", sa.String(20), nullable=False, server_default="direct"),
    )


def downgrade() -> None:
    op.drop_column("translation_test_runs", "method")
    op.drop_column("translation_runs", "method")
