"""Pure validation for a single persisted crawl seed — mirrors
app.domain.crawl_jobs' rules (same limits) but each seed is validated and
stored independently, since seeds no longer share one job-wide
max_documents/max_depth.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.crawl_jobs import (
    MAX_DEPTH_LIMIT,
    MAX_DOCUMENTS_LIMIT,
    InvalidCrawlJobConfig,
    validate_seed_url,
)

MAX_SEEDS_PER_COLLECTION = 25
MAX_LANGUAGE_LENGTH = 10


@dataclass(frozen=True)
class CrawlSeedConfig:
    url: str
    max_documents: int
    max_depth: int
    same_domain_only: bool
    language: str


def build_crawl_seed_config(
    *,
    url: str,
    max_documents: int,
    max_depth: int,
    same_domain_only: bool,
    language: str = "en",
) -> CrawlSeedConfig:
    normalized = validate_seed_url(url)
    if not (1 <= max_documents <= MAX_DOCUMENTS_LIMIT):
        raise InvalidCrawlJobConfig(f"max_documents must be between 1 and {MAX_DOCUMENTS_LIMIT}")
    if not (0 <= max_depth <= MAX_DEPTH_LIMIT):
        raise InvalidCrawlJobConfig(f"max_depth must be between 0 and {MAX_DEPTH_LIMIT}")
    normalized_language = language.strip().lower()
    if not (1 <= len(normalized_language) <= MAX_LANGUAGE_LENGTH):
        raise InvalidCrawlJobConfig(f"language must be between 1 and {MAX_LANGUAGE_LENGTH} characters")
    return CrawlSeedConfig(
        url=normalized,
        max_documents=max_documents,
        max_depth=max_depth,
        same_domain_only=same_domain_only,
        language=normalized_language,
    )
