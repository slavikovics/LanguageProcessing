from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


ANY_POS = "*"


class TranslationDictionaryEntry(Base):
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


class TranslationTestRun(Base):
    __tablename__ = "translation_test_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    source_lang: Mapped[str] = mapped_column(String(10), default="en")
    target_lang: Mapped[str] = mapped_column(String(10), default="fr")
    method: Mapped[str] = mapped_column(String(20), default="direct")
    status: Mapped[str] = mapped_column(String(20), default="pending")

    documents_total: Mapped[int] = mapped_column(Integer, default=0)
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class TranslationRun(Base):
    __tablename__ = "translation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    collection_id: Mapped[int | None] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=True
    )
    test_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("translation_test_runs.id", ondelete="CASCADE"), nullable=True
    )
    source_lang: Mapped[str] = mapped_column(String(10), default="en")
    target_lang: Mapped[str] = mapped_column(String(10), default="fr")
    method: Mapped[str] = mapped_column(String(20), default="direct")
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    translated_word_count: Mapped[int] = mapped_column(Integer, default=0)
    translated_text_word_count: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_ms: Mapped[float] = mapped_column(Float, default=0.0)
    diff_segments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class TranslationRunWord(Base):
    __tablename__ = "translation_run_words"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("translation_runs.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer)
    lemma: Mapped[str] = mapped_column(String(200))
    surface: Mapped[str] = mapped_column(String(200))
    pos: Mapped[str] = mapped_column(String(10))
    frequency: Mapped[int] = mapped_column(Integer)
    translation: Mapped[str | None] = mapped_column(String(200), nullable=True)
