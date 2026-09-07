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
    # Human-confirmed ground-truth language for LR2 (language identification)
    # — distinct from `language` above, which is only the crawl-time value
    # inherited from the collection and was never actually verified.
    confirmed_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # "train" | "test" | NULL (labeled but not yet assigned to either split).
    # Lives on the document, not on a separate "train"/"test" Collection, so
    # an operator can change a document's split without moving it anywhere.
    corpus_split: Mapped[str | None] = mapped_column(String(10), nullable=True)

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
    own max_documents/max_depth/same_domain_only/language and spawns one
    CrawlJob. Language is per-seed rather than per-collection so one
    collection can mix languages — e.g. an en.wikipedia.org seed and an
    fr.wikipedia.org seed feeding the same collection, each stamping its own
    documents with the right `Document.language` hint (LR2's ground truth is
    still the separate, human-confirmed `Document.confirmed_language`)."""

    __tablename__ = "crawl_seeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(2000))
    max_documents: Mapped[int] = mapped_column(Integer)
    max_depth: Mapped[int] = mapped_column(Integer)
    # When true, never follow a link to a different host, subdomains included.
    same_domain_only: Mapped[bool] = mapped_column(Boolean, default=False)
    # Stamped onto every document this seed's crawl fetches — see CrawlJob.language.
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (UniqueConstraint("collection_id", "url", name="uq_crawl_seed_collection_url"),)


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    seed_urls: Mapped[list[str]] = mapped_column(JSON)
    max_documents: Mapped[int] = mapped_column(Integer)
    max_depth: Mapped[int] = mapped_column(Integer)
    # Copied from the originating CrawlSeed at job-creation time (or from
    # Collection.language as a fallback for seed-less jobs, e.g. refresh) —
    # a later edit to the seed's language doesn't retroactively change a
    # queued/running/finished job's, same as its max_documents/max_depth.
    language: Mapped[str] = mapped_column(String(10), default="en")
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


class LangIdProfile(Base):
    """One trained profile per (method, language) for LR2's language
    identification. `language` is NULL only for "neural", whose single
    nn.Linear(4096,2) classifier is trained jointly across every labeled
    language rather than one independent profile per language like the
    lexical methods. `profile_data` holds whatever shape that method needs:
    frequent_words -> ranked word list, alphabetic -> char-frequency dict,
    neural -> {weights, bias, classes, loss_curve}."""

    __tablename__ = "lang_id_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    method: Mapped[str] = mapped_column(String(20))  # "frequent_words" | "alphabetic" | "neural"
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    profile_data: Mapped[dict] = mapped_column(JSON)
    source_document_count: Mapped[int] = mapped_column(Integer, default=0)
    source_char_count: Mapped[int] = mapped_column(Integer, default=0)
    built_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("method", "language", name="uq_lang_id_profile_method_language"),
    )


class LangIdTrainingJob(Base):
    """Tracks one neural-classifier training run so the frontend can show a
    live progress bar with the current loss/accuracy, the same way IndexJob
    tracks indexing progress."""

    __tablename__ = "lang_id_training_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    epochs_total: Mapped[int] = mapped_column(Integer, default=0)
    epochs_completed: Mapped[int] = mapped_column(Integer, default=0)
    current_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_train_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class LangIdRun(Base):
    """One method's identification pass over one collection's test-split
    documents — mirrors IndexJob's progress-tracking shape."""

    __tablename__ = "lang_id_runs"

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


class LangIdResult(Base):
    """One document's identification outcome under one run — the per-document
    row both the results table and the run's aggregate accuracy/speed stats
    are built from. `distances` holds every candidate language's distance
    (lower = closer, all three methods normalized to this convention — see
    app.domain.lang_id), so `predicted_language = min(distances, key=get)`
    is the one argmin rule shared by every method."""

    __tablename__ = "lang_id_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("lang_id_runs.id", ondelete="CASCADE"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    predicted_language: Mapped[str] = mapped_column(String(10))
    distances: Mapped[dict] = mapped_column(JSON)
    elapsed_ms: Mapped[float] = mapped_column(Float)
    # NULL only if the document's confirmed_language was cleared after the run.
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "document_id", name="uq_lang_id_result_run_document"),
    )


class LangIdRunMetric(Base):
    """Aggregate accuracy/precision/recall/F1 for one lang-id run, persisted
    the same way `MetricResult` caches search metrics — computed from
    `LangIdResult` rows whenever a run's summary is (re)requested."""

    __tablename__ = "lang_id_run_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("lang_id_runs.id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)


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
