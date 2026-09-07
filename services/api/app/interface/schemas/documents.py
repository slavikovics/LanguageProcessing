from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


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
