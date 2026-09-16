import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.domain.translation_seed_data import SEED_ENTRIES

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHUNK_SIZE = 5000

# 0015's rows were keyed by surface form, not lemma, causing identity-translation noise; replaces the whole non-curated slice with a lemma-pooled, re-filtered dictionary.
DICTIONARY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "app", "domain", "dictionaries", "en_fr_muse.tsv"
)

translation_dictionary_entries_table = sa.table(
    "translation_dictionary_entries",
    sa.column("source_lang", sa.String),
    sa.column("target_lang", sa.String),
    sa.column("source_lemma", sa.String),
    sa.column("pos", sa.String),
    sa.column("target_text", sa.String),
)


def _curated_keys() -> set[tuple[str, str]]:
    return {(lemma.lower(), pos or "*") for lemma, pos, _target in SEED_ENTRIES}


def _read_entries() -> list[dict]:
    curated_keys = _curated_keys()
    entries = []
    with open(DICTIONARY_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            source_lemma, pos, target_text = parts
            if (source_lemma.lower(), pos) in curated_keys:
                continue
            entries.append(
                {
                    "source_lang": "en",
                    "target_lang": "fr",
                    "source_lemma": source_lemma,
                    "pos": pos,
                    "target_text": target_text,
                }
            )
    return entries


def _delete_non_curated(conn) -> None:
    table = translation_dictionary_entries_table
    curated = list(_curated_keys())
    conn.execute(
        table.delete().where(
            sa.and_(
                table.c.source_lang == "en",
                table.c.target_lang == "fr",
                sa.tuple_(sa.func.lower(table.c.source_lemma), table.c.pos).not_in(curated),
            )
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    _delete_non_curated(conn)

    entries = _read_entries()
    table = translation_dictionary_entries_table
    for start in range(0, len(entries), CHUNK_SIZE):
        op.bulk_insert(table, entries[start : start + CHUNK_SIZE])


def downgrade() -> None:
    conn = op.get_bind()
    _delete_non_curated(conn)
