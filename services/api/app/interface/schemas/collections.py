from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


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
