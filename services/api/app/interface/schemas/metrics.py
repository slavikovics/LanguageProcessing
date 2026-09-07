from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


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
