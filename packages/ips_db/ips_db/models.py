"""The one place the database schema is defined. Both `api` and
`crawler-service` import these models rather than one importing the other's
internals — that is the actual service boundary, not the Python package
boundary.

Status columns use plain strings with literal defaults (not an import of
either service's domain enums) so this package has zero dependency on any
service's business logic — only `sqlalchemy`.
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


# Fixed width of the `document_embeddings.embedding` column. Every dense
# model's native vector (e.g. 768 for gte-multilingual-base) is zero-padded
# up to this length before being stored — cosine similarity is invariant to
# appending equal zero-padding to both compared vectors, and vectors are
# only ever compared within the same search_model_id, so one shared column
# width serves any number of dense models without a schema change per model.
MAX_EMBEDDING_DIM = 1024


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    # Bumped whenever a document in this collection is created/updated/
    # deleted/re-fetched — compared against the latest completed IndexJob's
    # finished_at to tell the UI the index is stale, since indexing a
    # document doesn't happen automatically on every mutation.
    documents_changed_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="collection")
    crawl_jobs: Mapped[list["CrawlJob"]] = relationship(back_populates="collection")


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
    """Registry of pluggable search algorithms (TF-IDF, dense embedding
    models, ...). This table's schema never changes when a new model is
    added — a new model is just one seeded row (see migrations), keyed by a
    stable `key` string that `search_runs.model_id` and the frontend refer
    to."""

    __tablename__ = "search_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))  # "tfidf" | "dense_embedding"
    dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class DocumentEmbedding(Base):
    """A document's dense vector under one registered model, zero-padded to
    MAX_EMBEDDING_DIM (see the constant's docstring above)."""

    __tablename__ = "document_embeddings"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
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
    """A persisted, editable crawl address for a collection — the source of
    truth the Crawl page's address list reads and writes. Each seed carries
    its own max_documents/max_depth/same_domain_only, independent of every
    other seed in the collection. Running the crawl spawns one CrawlJob per
    seed (see CrawlJobService.run_collection_crawl)."""

    __tablename__ = "crawl_seeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(2000))
    max_documents: Mapped[int] = mapped_column(Integer)
    max_depth: Mapped[int] = mapped_column(Integer)
    # When true, the crawl for this seed never follows a link to a different
    # host — including subdomains (en.example.com vs example.com) — useful
    # when a site fans out into other-language subdomains or links out a lot.
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
    # Copied from CrawlSeed.same_domain_only at job-creation time as the
    # exact host to stay on (netloc of the seed URL), or null when the crawl
    # may follow links anywhere — see CrawlWorker._enqueue_links.
    allowed_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # "crawl" discovers new pages via BFS; "refresh" re-fetches a fixed set
    # of already-known URLs in place (updates the existing Document rows
    # instead of inserting/skipping-on-duplicate) — see CollectionsPage's
    # "Обновить коллекцию" button.
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
