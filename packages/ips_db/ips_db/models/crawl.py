from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .collections import Collection


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

    collection: Mapped["Collection"] = relationship(back_populates="crawl_jobs")


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
