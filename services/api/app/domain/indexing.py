"""Pure indexing rules — no I/O. Mirrors app.domain.crawl_jobs: validation
errors and result shapes live here, orchestration lives in application/.
"""

from __future__ import annotations

from dataclasses import dataclass


class IndexingError(ValueError):
    pass


@dataclass(frozen=True)
class IndexingSummary:
    collection_id: int
    documents_indexed: int
    terms_indexed: int
