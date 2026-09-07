from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class CrawlJobCreate(BaseModel):
    collection_id: int
    seed_urls: list[str] = Field(min_length=1, max_length=25)
    max_documents: int = Field(gt=0, le=2000)
    max_depth: int = Field(ge=0, le=5)


class CrawlJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    seed_urls: list[str]
    max_documents: int
    max_depth: int
    allowed_domain: str | None = None
    mode: str
    status: str
    documents_fetched: int
    urls_queued: int
    urls_visited: int
    urls_failed: int
    error_message: str | None
    created_at: dt.datetime
    started_at: dt.datetime | None
    finished_at: dt.datetime | None


class CrawlSeedCreate(BaseModel):
    url: str
    max_documents: int = Field(gt=0, le=2000)
    max_depth: int = Field(ge=0, le=5)
    same_domain_only: bool = False
    language: str = "en"


class CrawlSeedUpdate(BaseModel):
    url: str
    max_documents: int = Field(gt=0, le=2000)
    max_depth: int = Field(ge=0, le=5)
    same_domain_only: bool = False
    language: str = "en"


class CrawlSeedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    url: str
    max_documents: int
    max_depth: int
    same_domain_only: bool
    language: str
    created_at: dt.datetime


class CrawlUrlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    depth: int
    status: str
    error: str | None


class CrawlJobProgressOut(BaseModel):
    job: CrawlJobOut
    recent_urls: list[CrawlUrlOut]
