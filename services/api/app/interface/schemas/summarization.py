from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class SelectedSentenceOut(BaseModel):
    index: int
    text: str
    weight: float


class SummarizeDocumentRequest(BaseModel):
    methods: list[str] | None = None
    sentence_count: int = 10


class SummaryOutcomeOut(BaseModel):
    method: str
    sentences: list[SelectedSentenceOut]
    total_sentences: int
    elapsed_ms: float
    compression_ratio: float


class KeywordGroupOut(BaseModel):
    term: str
    children: list[str]


class SummarizeDocumentResponseOut(BaseModel):
    document_id: int
    keywords: list[KeywordGroupOut]
    results: list[SummaryOutcomeOut]


class DocumentSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int | None
    document_id: int
    method: str
    sentence_count: int
    summary_text: str
    summary_sentence_indices: list[int]
    total_sentences: int
    elapsed_ms: float
    created_at: dt.datetime


class PolishSummaryRequest(BaseModel):
    language: str | None = None


class PolishSummaryOut(BaseModel):
    document_summary_id: int
    model: str
    polished_markdown: str


class SummarizationRunCreate(BaseModel):
    collection_id: int
    methods: list[str] = Field(min_length=1)


class SummarizationRunOut(BaseModel):
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


class SummarizationRunSummaryOut(BaseModel):
    run_id: int
    method: str
    documents_summarized: int
    mean_elapsed_ms: float
    mean_compression_ratio: float
    mean_sentence_count: float


class SummarizationCompareResponseOut(BaseModel):
    summaries: list[SummarizationRunSummaryOut]
