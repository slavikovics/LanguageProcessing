from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobContext:
    id: int
    collection_id: int
    language: str
    max_documents: int
    max_depth: int
    mode: str
    allowed_domain: str | None = None
