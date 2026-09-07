"""LR2: language identification (frequent-words/alphabetic/neural methods).

Adds `confirmed_language`/`corpus_split` to `documents` — crawled documents
carry only the collection-inherited `language`, never a verified ground
truth, so identification needs a human-confirmed field plus a train/test
split flag independent of which collection a document was crawled into.

Adds four new tables: `lang_id_profiles` (one trained profile per method+
language, NULL language for the single joint neural classifier),
`lang_id_training_jobs` (live progress for neural training, mirrors
IndexJob), `lang_id_runs` (one method's identification pass over a
collection's test split, mirrors IndexJob), and `lang_id_results`
(per-document outcome under one run).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("confirmed_language", sa.String(10), nullable=True))
    op.add_column("documents", sa.Column("corpus_split", sa.String(10), nullable=True))

    op.create_table(
        "lang_id_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("profile_data", sa.JSON(), nullable=False),
        sa.Column("source_document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("built_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("method", "language", name="uq_lang_id_profile_method_language"),
    )

    op.create_table(
        "lang_id_training_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("epochs_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("epochs_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_loss", sa.Float(), nullable=True),
        sa.Column("current_train_accuracy", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "lang_id_runs",
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
        "lang_id_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id", sa.Integer(), sa.ForeignKey("lang_id_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("predicted_language", sa.String(10), nullable=False),
        sa.Column("distances", sa.JSON(), nullable=False),
        sa.Column("elapsed_ms", sa.Float(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("run_id", "document_id", name="uq_lang_id_result_run_document"),
    )


def downgrade() -> None:
    op.drop_table("lang_id_results")
    op.drop_table("lang_id_runs")
    op.drop_table("lang_id_training_jobs")
    op.drop_table("lang_id_profiles")
    op.drop_column("documents", "corpus_split")
    op.drop_column("documents", "confirmed_language")
