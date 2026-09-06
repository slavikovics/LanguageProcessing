"""The one place the database schema is defined; `api` and `crawler-service`
both import these models instead of one importing the other's internals.
Status columns use plain strings (not either service's domain enums) so this
package depends on nothing but sqlalchemy.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# Every dense model's vector is zero-padded to this width before storage —
# cosine similarity is invariant to equal zero-padding on both sides, so one
# column width serves any model without a schema change.
MAX_EMBEDDING_DIM = 4096


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    # Bumped on any document change; compared to the latest IndexJob's
    # finished_at so the UI can tell the index is stale.
    documents_changed_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    # passive_deletes: rely on the DB's ON DELETE CASCADE — SQLAlchemy's default
    # of nulling child FKs first would fail since those FK columns are NOT NULL.
    documents: Mapped[list["Document"]] = relationship(
        back_populates="collection", passive_deletes=True
    )
    crawl_jobs: Mapped[list["CrawlJob"]] = relationship(
        back_populates="collection", passive_deletes=True
    )


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

    collection: Mapped[Collection] = relationship(back_populates="documents")

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


class SearchModel(Base):
    """Registry of pluggable search algorithms — a new model is just a seeded row."""

    __tablename__ = "search_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))  # "tfidf" | "dense_embedding"
    dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


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


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class SearchRun(Base):
    __tablename__ = "search_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("queries.id", ondelete="CASCADE"))
    model_id: Mapped[int] = mapped_column(ForeignKey("search_models.id", ondelete="RESTRICT"))
    executed_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class SearchResult(Base):
    __tablename__ = "search_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_run_id: Mapped[int] = mapped_column(ForeignKey("search_runs.id", ondelete="CASCADE"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)


class RelevanceJudgment(Base):
    __tablename__ = "relevance_judgments"

    query_id: Mapped[int] = mapped_column(ForeignKey("queries.id", ondelete="CASCADE"), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    is_relevant: Mapped[bool] = mapped_column(Boolean)


class MetricResult(Base):
    __tablename__ = "metric_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_run_id: Mapped[int] = mapped_column(ForeignKey("search_runs.id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)


class CrawlSeed(Base):
    """A persisted, editable crawl address for a collection; each seed has its
    own max_documents/max_depth/same_domain_only and spawns one CrawlJob."""

    __tablename__ = "crawl_seeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(2000))
    max_documents: Mapped[int] = mapped_column(Integer)
    max_depth: Mapped[int] = mapped_column(Integer)
    # When true, never follow a link to a different host, subdomains included.
    same_domain_only: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (UniqueConstraint("collection_id", "url", name="uq_crawl_seed_collection_url"),)


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    seed_urls: Mapped[list[str]] = mapped_column(JSON)
    max_documents: Mapped[int] = mapped_column(Integer)
    max_depth: Mapped[int] = mapped_column(Integer)
    # Host to stay on (from the seed URL), or null if links may go anywhere.
    allowed_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # "crawl" discovers new pages via BFS; "refresh" re-fetches known URLs in place.
    mode: Mapped[str] = mapped_column(String(20), default="crawl")

    documents_fetched: Mapped[int] = mapped_column(Integer, default=0)
    urls_queued: Mapped[int] = mapped_column(Integer, default=0)
    urls_visited: Mapped[int] = mapped_column(Integer, default=0)
    urls_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    collection: Mapped[Collection] = relationship(back_populates="crawl_jobs")


class IndexJob(Base):
    __tablename__ = "index_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="pending")

    documents_total: Mapped[int] = mapped_column(Integer, default=0)
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    terms_indexed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class CrawlUrl(Base):
    __tablename__ = "crawl_urls"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("crawl_jobs.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(2000))
    depth: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    discovered_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("crawl_urls.id", ondelete="SET NULL"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("job_id", "url", name="uq_crawl_url_job_url"),)
