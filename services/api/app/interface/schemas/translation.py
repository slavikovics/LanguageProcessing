from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, model_validator

from app.domain.translation import DEFAULT_SOURCE_LANGUAGE, DEFAULT_TARGET_LANGUAGE


class TranslateRequest(BaseModel):
    document_id: int | None = None
    text: str | None = None
    collection_id: int | None = None
    source_lang: str = DEFAULT_SOURCE_LANGUAGE
    target_lang: str = DEFAULT_TARGET_LANGUAGE

    @model_validator(mode="after")
    def _require_source(self) -> "TranslateRequest":
        if self.document_id is None and not (self.text and self.text.strip()):
            raise ValueError("either document_id or text must be provided")
        return self


class TranslationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int | None
    collection_id: int | None
    source_lang: str
    target_lang: str
    source_text: str
    translated_text: str
    word_count: int
    translated_word_count: int
    elapsed_ms: float
    created_at: dt.datetime


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
