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

# Migration 0015 bulk-inserted MUSE's raw induced en->fr dictionary keyed by
# whatever surface word it happened to appear as (source_lemma stored the raw
# frequency-list token, not a computed lemma — "did", "went", "goes" each got
# their own disconnected row instead of pooling under "do"/"go"), and picked
# whatever MUSE candidate came first even when that candidate was just the
# English word mapped to itself. MUSE's automatically-induced dictionaries are
# seeded from identical-string pairs and are especially noisy for
# high-frequency function words ("her her", "will will", "did did", ...) —
# nearly half of the bulk-inserted rows ended up with target_text equal to the
# source word, concentrated in exactly the closed-class categories (pronouns,
# determiners, auxiliaries, prepositions...) that dominate word counts in real
# text, which is what made direct translations look like they left "too many
# words the same".
#
# en_fr_muse.tsv has been regenerated: entries are now pooled by the actual
# spaCy-computed lemma (so "did"/"goes"/"went" contribute their MUSE
# candidates to one "do" entry instead of three disconnected ones), preferring
# a genuine (non-self) translation whenever any inflected form of the lemma
# has one anywhere in MUSE's data. Closed-class words where no inflected form
# has a real translation are dropped entirely (left untranslated by the
# direct-translation system) instead of keeping a fabricated self-translation.
# Open-class words with no non-self candidate anywhere in MUSE are still
# stored as identical — many of those are genuine EN/FR cognates and
# loanwords (e.g. "virus", "style").
#
# Because the old rows were keyed by surface form and the new ones by lemma,
# there's no reliable per-row correspondence to update in place, so this
# migration replaces the whole non-curated slice: every row migration 0015
# bulk-inserted is removed and the regenerated file is inserted fresh.
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
    # The pre-fix per-surface-word data isn't recoverable from what's on disk
    # now; downgrading just clears the regenerated rows back to empty, same as
    # 0015's own downgrade() does for its bulk import.
    conn = op.get_bind()
    _delete_non_curated(conn)
