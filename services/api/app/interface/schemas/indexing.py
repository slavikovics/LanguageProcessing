from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


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
