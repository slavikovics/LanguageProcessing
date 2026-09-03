from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class CollectionCreate(BaseModel):
    name: str
    language: str = "en"


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    language: str
    created_at: dt.datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    title: str
    url: str
    language: str
    char_count: int
    fetched_at: dt.datetime


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
    status: str
    documents_fetched: int
    urls_queued: int
    urls_visited: int
    urls_failed: int
    error_message: str | None
    created_at: dt.datetime
    started_at: dt.datetime | None
    finished_at: dt.datetime | None


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
