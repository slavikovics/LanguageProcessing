
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

MAX_SEED_URLS = 25
MAX_DOCUMENTS_LIMIT = 2000
MAX_DEPTH_LIMIT = 5


class InvalidCrawlJobConfig(ValueError):
    pass


@dataclass(frozen=True)
class CrawlJobConfig:
    collection_id: int
    seed_urls: tuple[str, ...]
    max_documents: int
    max_depth: int


def validate_seed_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidCrawlJobConfig(f"'{url}' is not a valid http(s) URL")
    return url.strip()


def build_crawl_job_config(
    *,
    collection_id: int,
    seed_urls: list[str],
    max_documents: int,
    max_depth: int,
) -> CrawlJobConfig:
    if not seed_urls:
        raise InvalidCrawlJobConfig("at least one seed URL is required")
    if len(seed_urls) > MAX_SEED_URLS:
        raise InvalidCrawlJobConfig(f"at most {MAX_SEED_URLS} seed URLs are allowed")

    normalized = tuple(dict.fromkeys(validate_seed_url(url) for url in seed_urls))

    if not (1 <= max_documents <= MAX_DOCUMENTS_LIMIT):
        raise InvalidCrawlJobConfig(
            f"max_documents must be between 1 and {MAX_DOCUMENTS_LIMIT}"
        )
    if not (0 <= max_depth <= MAX_DEPTH_LIMIT):
        raise InvalidCrawlJobConfig(f"max_depth must be between 0 and {MAX_DEPTH_LIMIT}")

    return CrawlJobConfig(
        collection_id=collection_id,
        seed_urls=normalized,
        max_documents=max_documents,
        max_depth=max_depth,
    )


def build_refresh_job_config(*, collection_id: int, urls: list[str]) -> CrawlJobConfig:
    if not urls:
        raise InvalidCrawlJobConfig("collection has no documents with a URL to refresh")
    if len(urls) > MAX_DOCUMENTS_LIMIT:
        raise InvalidCrawlJobConfig(f"at most {MAX_DOCUMENTS_LIMIT} documents can be refreshed at once")

    normalized = tuple(dict.fromkeys(validate_seed_url(url) for url in urls))

    return CrawlJobConfig(
        collection_id=collection_id,
        seed_urls=normalized,
        max_documents=len(normalized),
        max_depth=0,
    )
