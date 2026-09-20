from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "translation_runs",
        sa.Column("diff_segments", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("translation_runs", "diff_segments")
