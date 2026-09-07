from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


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
