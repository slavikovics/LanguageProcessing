from __future__ import annotations

import datetime as dt

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


ANY_POS = "*"
"""Sentinel `pos` value meaning "matches any part of speech". A real NULL
can't be used for this: Postgres treats every NULL as distinct for the
purposes of a UNIQUE constraint, so two NULL-pos rows for the same lemma
would silently bypass duplicate detection."""


class TranslationDictionaryEntry(Base):
    """One (source_lemma, POS) -> target_text mapping used by the direct
    (word-for-word) translation system. `pos` is `ANY_POS` for an entry that
    covers a lemma regardless of part of speech (checked as a fallback after
    a POS-specific entry)."""

    __tablename__ = "translation_dictionary_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_lang: Mapped[str] = mapped_column(String(10))
    target_lang: Mapped[str] = mapped_column(String(10))
    source_lemma: Mapped[str] = mapped_column(String(200))
    pos: Mapped[str] = mapped_column(String(10), default=ANY_POS)
    target_text: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "source_lang", "target_lang", "source_lemma", "pos", name="uq_translation_dictionary_entry"
        ),
    )


class TranslationRun(Base):
    """One machine-translation pass over a text (either a document from a
    collection or pasted free text)."""

    __tablename__ = "translation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    collection_id: Mapped[int | None] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=True
    )
    source_lang: Mapped[str] = mapped_column(String(10), default="en")
    target_lang: Mapped[str] = mapped_column(String(10), default="fr")
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    translated_word_count: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class TranslationRunWord(Base):
    """A row of the frequency-ordered word list (tab 1) for a translation run."""

    __tablename__ = "translation_run_words"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("translation_runs.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer)
    lemma: Mapped[str] = mapped_column(String(200))
    surface: Mapped[str] = mapped_column(String(200))
    pos: Mapped[str] = mapped_column(String(10))
    frequency: Mapped[int] = mapped_column(Integer)
    translation: Mapped[str | None] = mapped_column(String(200), nullable=True)
