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
    confirmed_language: str | None = None
    corpus_split: str | None = None


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
    confirmed_language: str | None = None
    corpus_split: str | None = None


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
    model: str = "tfidf"


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
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    query_id: int
    search_run_id: int
    query_text: str
    model: str
    model_label: str
    hits: list[SearchHitOut]


class SearchModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str
    kind: str
    dimension: int | None


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
    precision_at_5: float
    precision_at_10: float
    recall_at_5: float
    recall_at_10: float
    f1_at_5: float
    f1_at_10: float
    average_precision: float
    r_precision: float
    curve: list[tuple[float, float]]


class CollectionMetricsSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    collection_id: int
    model: str
    model_label: str
    map: float
    mean_recall_at_5: float
    mean_recall_at_10: float
    mean_f1_at_5: float
    mean_f1_at_10: float
    mean_r_precision: float
    mean_precision_at_5: float
    mean_precision_at_10: float
    queries: list[QueryMetricsOut]
    curve: list[tuple[float, float]]
    unscored_judged_queries: int = 0


class MetricsCompareResponseOut(BaseModel):
    summaries: list[CollectionMetricsSummaryOut]


# -- LR2: language identification -------------------------------------------


class LanguageLabelIn(BaseModel):
    confirmed_language: str | None = None
    corpus_split: str | None = None


class LabelProgressOut(BaseModel):
    total: int
    labeled: int
    unlabeled: int
    train_count: int
    test_count: int


class AutoSplitResultOut(BaseModel):
    train_assigned: int
    test_assigned: int


class LangIdProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    method: str
    language: str | None
    source_document_count: int
    source_char_count: int
    built_at: dt.datetime


class BuildLexicalProfileRequest(BaseModel):
    language: str


class IdentificationOutcomeOut(BaseModel):
    method: str
    predicted_language: str
    distances: dict[str, float]
    elapsed_ms: float


class IdentifyDocumentRequest(BaseModel):
    document_id: int
    methods: list[str] | None = None


class IdentifyUrlRequest(BaseModel):
    url: str
    methods: list[str] | None = None


class IdentifyTextRequest(BaseModel):
    text: str
    is_html: bool = False
    methods: list[str] | None = None


class IdentifyResponseOut(BaseModel):
    results: list[IdentificationOutcomeOut]


class LangIdTrainingJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    epochs_total: int
    epochs_completed: int
    current_loss: float | None
    current_train_accuracy: float | None
    error_message: str | None
    created_at: dt.datetime
    started_at: dt.datetime | None
    finished_at: dt.datetime | None


class LangIdRunCreate(BaseModel):
    collection_id: int
    methods: list[str] = Field(min_length=1)


class LangIdRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    method: str
    status: str
    documents_total: int
    documents_processed: int
    error_message: str | None
    created_at: dt.datetime
    started_at: dt.datetime | None
    finished_at: dt.datetime | None


class LangIdResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    document_id: int
    predicted_language: str
    distances: dict[str, float]
    elapsed_ms: float
    is_correct: bool | None


class LangIdRunSummaryOut(BaseModel):
    run_id: int
    method: str
    documents_evaluated: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    mean_elapsed_ms: float
    confusion: dict[str, dict[str, int]]


class LangIdCompareResponseOut(BaseModel):
    summaries: list[LangIdRunSummaryOut]
