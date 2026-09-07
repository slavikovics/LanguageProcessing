from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


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
