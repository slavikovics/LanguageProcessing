import pytest

from app.domain.crawl_jobs import InvalidCrawlJobConfig, build_crawl_job_config


def test_build_crawl_job_config_happy_path():
    config = build_crawl_job_config(
        collection_id=1,
        seed_urls=["https://example.com/a", "https://example.com/b"],
        max_documents=50,
        max_depth=2,
    )
    assert config.collection_id == 1
    assert config.seed_urls == ("https://example.com/a", "https://example.com/b")
    assert config.max_documents == 50
    assert config.max_depth == 2


def test_build_crawl_job_config_deduplicates_seed_urls():
    config = build_crawl_job_config(
        collection_id=1,
        seed_urls=["https://example.com/a", "https://example.com/a"],
        max_documents=10,
        max_depth=1,
    )
    assert config.seed_urls == ("https://example.com/a",)


def test_build_crawl_job_config_rejects_empty_seed_list():
    with pytest.raises(InvalidCrawlJobConfig):
        build_crawl_job_config(collection_id=1, seed_urls=[], max_documents=10, max_depth=1)


def test_build_crawl_job_config_rejects_non_http_url():
    with pytest.raises(InvalidCrawlJobConfig):
        build_crawl_job_config(
            collection_id=1, seed_urls=["ftp://example.com"], max_documents=10, max_depth=1
        )


def test_build_crawl_job_config_rejects_out_of_range_max_documents():
    with pytest.raises(InvalidCrawlJobConfig):
        build_crawl_job_config(
            collection_id=1, seed_urls=["https://example.com"], max_documents=0, max_depth=1
        )


def test_build_crawl_job_config_rejects_negative_depth():
    with pytest.raises(InvalidCrawlJobConfig):
        build_crawl_job_config(
            collection_id=1, seed_urls=["https://example.com"], max_documents=10, max_depth=-1
        )


def test_build_crawl_job_config_rejects_too_many_seed_urls():
    urls = [f"https://example.com/{i}" for i in range(26)]
    with pytest.raises(InvalidCrawlJobConfig):
        build_crawl_job_config(collection_id=1, seed_urls=urls, max_documents=10, max_depth=1)
