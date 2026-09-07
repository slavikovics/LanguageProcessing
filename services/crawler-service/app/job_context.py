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
    # Exact host (netloc) this job's discovered links must stay on — including
    # rejecting subdomains — or None when links may go anywhere.
    allowed_domain: str | None = None
