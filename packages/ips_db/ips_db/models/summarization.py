from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SummarizationRun(Base):

    __tablename__ = "summarization_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")

    documents_total: Mapped[int] = mapped_column(Integer, default=0)
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class DocumentSummary(Base):

    __tablename__ = "document_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("summarization_runs.id", ondelete="CASCADE"), nullable=True
    )
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    method: Mapped[str] = mapped_column(String(20))

    sentence_count: Mapped[int] = mapped_column(Integer)
    summary_text: Mapped[str] = mapped_column(Text)
    summary_sentence_indices: Mapped[list] = mapped_column(JSON)
    total_sentences: Mapped[int] = mapped_column(Integer, default=0)
    total_chars: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_ms: Mapped[float] = mapped_column(Float)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class DocumentSummaryPolish(Base):

    __tablename__ = "document_summary_polishes"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_summary_id: Mapped[int] = mapped_column(
        ForeignKey("document_summaries.id", ondelete="CASCADE")
    )
    model: Mapped[str] = mapped_column(String(100))
    polished_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
