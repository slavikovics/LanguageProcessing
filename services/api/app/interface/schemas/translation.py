from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.domain.translation import DEFAULT_SOURCE_LANGUAGE, DEFAULT_TARGET_LANGUAGE

TranslationMethod = Literal["direct", "transfer", "neural"]


class TranslateRequest(BaseModel):
    document_id: int | None = None
    text: str | None = None
    collection_id: int | None = None
    source_lang: str = DEFAULT_SOURCE_LANGUAGE
    target_lang: str = DEFAULT_TARGET_LANGUAGE
    method: TranslationMethod = "direct"

    @model_validator(mode="after")
    def _require_source(self) -> "TranslateRequest":
        if self.document_id is None and not (self.text and self.text.strip()):
            raise ValueError("either document_id or text must be provided")
        return self


class DiffSegmentOut(BaseModel):
    text: str
    changed: bool


class TranslationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int | None
    collection_id: int | None
    test_run_id: int | None
    source_lang: str
    target_lang: str
    method: str
    source_text: str
    translated_text: str
    word_count: int
    translated_word_count: int
    translated_text_word_count: int
    elapsed_ms: float
    diff_segments: list[DiffSegmentOut] | None
    created_at: dt.datetime


class TranslationTestRunCreate(BaseModel):
    collection_id: int
    source_lang: str = DEFAULT_SOURCE_LANGUAGE
    target_lang: str = DEFAULT_TARGET_LANGUAGE
    method: TranslationMethod = "direct"


class TranslationTestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    source_lang: str
    target_lang: str
    method: str
    status: str
    documents_total: int
    documents_processed: int
    error_message: str | None
    created_at: dt.datetime
    started_at: dt.datetime | None
    finished_at: dt.datetime | None


class TranslationRunSummaryOut(BaseModel):
    run_id: int
    source_lang: str
    target_lang: str
    method: str
    documents_translated: int
    mean_elapsed_ms: float
    mean_word_count: float
    mean_translated_word_count: float
    mean_translated_text_word_count: float
    mean_coverage_ratio: float


class TranslationRunWordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    lemma: str
    surface: str
    pos: str
    frequency: int
    translation: str | None


class SentenceListOut(BaseModel):
    sentences: list[str]


class ParseSentenceRequest(BaseModel):
    text: str


class SyntaxTokenOut(BaseModel):
    position: int
    text: str
    lemma: str
    pos: str
    dep: str
    head_position: int | None
    head_text: str | None
    morph: dict[str, str]
    is_punct: bool


class ParseSentenceResponseOut(BaseModel):
    tokens: list[SyntaxTokenOut]


class TranslationDictionaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_lang: str
    target_lang: str
    source_lemma: str
    pos: str
    target_text: str
    notes: str | None
    created_at: dt.datetime
    updated_at: dt.datetime


class TranslationDictionaryPageOut(BaseModel):
    items: list[TranslationDictionaryEntryOut]
    total: int


class TranslationDictionaryEntryCreate(BaseModel):
    source_lang: str = DEFAULT_SOURCE_LANGUAGE
    target_lang: str = DEFAULT_TARGET_LANGUAGE
    source_lemma: str
    pos: str | None = None
    target_text: str
    notes: str | None = None


class TranslationDictionaryEntryUpdate(BaseModel):
    target_text: str | None = None
    pos: str | None = None
    notes: str | None = None
