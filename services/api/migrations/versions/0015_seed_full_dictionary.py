import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.domain.translation_seed_data import SEED_ENTRIES

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHUNK_SIZE = 5000

# A real, broad-coverage EN -> FR bilingual lexicon (MUSE, Facebook Research:
# https://github.com/facebookresearch/MUSE, dictionaries/en-fr.txt), deduped
# to one translation per source word, filtered to alphabetic pairs, and kept
# only for source words in the top 50k most common English words (hermitdave
# /FrequencyWords, subtitle-frequency corpus) — this drops MUSE's long tail
# of place names/abbreviations picked up from its training corpus. Each word
# is POS-tagged out of context with spaCy (en_core_web_sm) rather than left
# under an "any POS" sentinel, so the dictionary carries real grammatical
# information; entries whose (lemma, pos) already exists in the curated set
# from migration 0013 are skipped to avoid a unique-constraint clash.
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


def _read_entries() -> list[dict]:
    curated_keys = {(lemma.lower(), pos) for lemma, pos, _target in SEED_ENTRIES}
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


def upgrade() -> None:
    entries = _read_entries()
    for start in range(0, len(entries), CHUNK_SIZE):
        op.bulk_insert(translation_dictionary_entries_table, entries[start : start + CHUNK_SIZE])


def downgrade() -> None:
    entries = _read_entries()
    pairs = [(entry["source_lemma"], entry["pos"]) for entry in entries]
    conn = op.get_bind()
    table = translation_dictionary_entries_table
    for start in range(0, len(pairs), CHUNK_SIZE):
        chunk = pairs[start : start + CHUNK_SIZE]
        conn.execute(
            table.delete().where(
                sa.tuple_(table.c.source_lemma, table.c.pos).in_(chunk)
            )
        )
