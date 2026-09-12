from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "summarization_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("documents_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "document_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("summarization_runs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("sentence_count", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("summary_sentence_indices", sa.JSON(), nullable=False),
        sa.Column("total_sentences", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("elapsed_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "document_summary_polishes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_summary_id",
            sa.Integer(),
            sa.ForeignKey("document_summaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("polished_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("document_summary_polishes")
    op.drop_table("document_summaries")
    op.drop_table("summarization_runs")
