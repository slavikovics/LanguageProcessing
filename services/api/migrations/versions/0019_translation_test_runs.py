from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "translation_test_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_lang", sa.String(10), nullable=False, server_default="en"),
        sa.Column("target_lang", sa.String(10), nullable=False, server_default="fr"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("documents_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "translation_runs",
        sa.Column(
            "test_run_id",
            sa.Integer(),
            sa.ForeignKey("translation_test_runs.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "translation_runs",
        sa.Column("translated_text_word_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_translation_runs_test_run_id", "translation_runs", ["test_run_id"])


def downgrade() -> None:
    op.drop_index("ix_translation_runs_test_run_id", table_name="translation_runs")
    op.drop_column("translation_runs", "translated_text_word_count")
    op.drop_column("translation_runs", "test_run_id")
    op.drop_table("translation_test_runs")
