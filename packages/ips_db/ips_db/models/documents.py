from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from .base import Base, MAX_EMBEDDING_DIM

if TYPE_CHECKING:
    from .collections import Collection


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    clean_text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="en")
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    published_date: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    # Human-confirmed ground-truth language for LR2 (language identification)
    # — distinct from `language` above, which is only the crawl-time value
    # inherited from the collection and was never actually verified.
    confirmed_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # "train" | "test" | NULL (labeled but not yet assigned to either split).
    # Lives on the document, not on a separate "train"/"test" Collection, so
    # an operator can change a document's split without moving it anywhere.
    corpus_split: Mapped[str | None] = mapped_column(String(10), nullable=True)

    collection: Mapped["Collection"] = relationship(back_populates="documents")

    __table_args__ = (UniqueConstraint("collection_id", "url", name="uq_document_collection_url"),)


class Term(Base):
    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    lemma: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10), default="en")

    __table_args__ = (UniqueConstraint("lemma", "language", name="uq_term_lemma_language"),)


class DocumentTerm(Base):
    __tablename__ = "document_terms"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"), primary_key=True)
    tf: Mapped[int] = mapped_column(Integer)


class TermWeight(Base):
    __tablename__ = "term_weights"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"), primary_key=True)
    weight: Mapped[float] = mapped_column(Float)


class DocumentChunk(Base):
    """A document split into context-sized pieces for dense embedding, so a
    long document isn't silently truncated by the encoder."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),)


class DocumentChunkEmbedding(Base):
    """A chunk's dense vector under one registered model, zero-padded to MAX_EMBEDDING_DIM."""

    __tablename__ = "document_chunk_embeddings"

    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    search_model_id: Mapped[int] = mapped_column(
        ForeignKey("search_models.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(MAX_EMBEDDING_DIM))
