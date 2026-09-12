from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.domain.translation_seed_data import SEED_ENTRIES

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

translation_dictionary_entries_table = sa.table(
    "translation_dictionary_entries",
    sa.column("source_lang", sa.String),
    sa.column("target_lang", sa.String),
    sa.column("source_lemma", sa.String),
    sa.column("pos", sa.String),
    sa.column("target_text", sa.String),
)


def upgrade() -> None:
    op.create_table(
        "translation_dictionary_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_lang", sa.String(10), nullable=False),
        sa.Column("target_lang", sa.String(10), nullable=False),
        sa.Column("source_lemma", sa.String(200), nullable=False),
        sa.Column("pos", sa.String(10), nullable=True),
        sa.Column("target_text", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "source_lang", "target_lang", "source_lemma", "pos", name="uq_translation_dictionary_entry"
        ),
    )
    op.create_index(
        "ix_translation_dictionary_entries_lemma",
        "translation_dictionary_entries",
        ["source_lang", "target_lang", "source_lemma"],
    )

    op.create_table(
        "translation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_lang", sa.String(10), nullable=False, server_default="en"),
        sa.Column("target_lang", sa.String(10), nullable=False, server_default="fr"),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("translated_word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("elapsed_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "translation_run_words",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("translation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("lemma", sa.String(200), nullable=False),
        sa.Column("surface", sa.String(200), nullable=False),
        sa.Column("pos", sa.String(10), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("translation", sa.String(200), nullable=True),
    )
    op.create_index(
        "ix_translation_run_words_run_id", "translation_run_words", ["run_id"]
    )

    op.bulk_insert(
        translation_dictionary_entries_table,
        [
            {
                "source_lang": "en",
                "target_lang": "fr",
                "source_lemma": lemma,
                "pos": pos,
                "target_text": target,
            }
            for lemma, pos, target in SEED_ENTRIES
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_translation_run_words_run_id", table_name="translation_run_words")
    op.drop_table("translation_run_words")
    op.drop_table("translation_runs")
    op.drop_index(
        "ix_translation_dictionary_entries_lemma", table_name="translation_dictionary_entries"
    )
    op.drop_table("translation_dictionary_entries")
