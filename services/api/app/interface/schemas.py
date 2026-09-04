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
    document_count: int = 0
    documents_changed_at: dt.datetime | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    title: str
    url: str | None
    language: str
    char_count: int
    fetched_at: dt.datetime


class DocumentDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    title: str
    url: str | None
    clean_text: str
    language: str
    char_count: int
    fetched_at: dt.datetime


class DocumentCreate(BaseModel):
    title: str
    url: str | None = None
    clean_text: str


class DocumentUpdate(BaseModel):
    title: str
    url: str | None = None
    clean_text: str


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


class CrawlSeedUpdate(BaseModel):
    url: str
    max_documents: int = Field(gt=0, le=2000)
    max_depth: int = Field(ge=0, le=5)
    same_domain_only: bool = False


class CrawlSeedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    url: str
    max_documents: int
    max_depth: int
    same_domain_only: bool
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


class IndexJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    status: str
    documents_total: int
    documents_processed: int
    terms_indexed: int | None
    error_message: str | None
    created_at: dt.datetime
    started_at: dt.datetime | None
    finished_at: dt.datetime | None


class SearchRequest(BaseModel):
    collection_id: int
    text: str
    top_k: int = 10


class SearchHitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    title: str
    url: str | None
    fetched_at: dt.datetime
    rank: int
    score: float
    snippet: str
    matched_terms: list[str]


class SearchResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query_id: int
    search_run_id: int
    query_text: str
    hits: list[SearchHitOut]


class QueryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    text: str
    created_at: dt.datetime


class RelevanceJudgmentIn(BaseModel):
    is_relevant: bool


class RelevanceJudgmentOut(BaseModel):
    document_id: int
    is_relevant: bool


class QueryMetricsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query_id: int
    query_text: str
    search_run_id: int
    retrieved_count: int
    relevant_count: int
    precision: float
    recall: float
    f1: float
    precision_at_5: float
    precision_at_10: float
    average_precision: float
    r_precision: float
    curve: list[tuple[float, float]]


class CollectionMetricsSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collection_id: int
    map: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    queries: list[QueryMetricsOut]
    curve: list[tuple[float, float]]
