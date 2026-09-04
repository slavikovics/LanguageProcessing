import pytest

from app.domain.crawl_jobs import InvalidCrawlJobConfig
from app.domain.crawl_seeds import build_crawl_seed_config


def test_build_crawl_seed_config_happy_path():
    config = build_crawl_seed_config(
        url="https://example.com/a", max_documents=50, max_depth=2, same_domain_only=True
    )
    assert config.url == "https://example.com/a"
    assert config.max_documents == 50
    assert config.max_depth == 2
    assert config.same_domain_only is True


def test_build_crawl_seed_config_defaults_same_domain_only_false():
    config = build_crawl_seed_config(
        url="https://example.com/a", max_documents=10, max_depth=1, same_domain_only=False
    )
    assert config.same_domain_only is False


def test_build_crawl_seed_config_rejects_non_http_url():
    with pytest.raises(InvalidCrawlJobConfig):
        build_crawl_seed_config(url="ftp://example.com", max_documents=10, max_depth=1, same_domain_only=False)


def test_build_crawl_seed_config_rejects_out_of_range_max_documents():
    with pytest.raises(InvalidCrawlJobConfig):
        build_crawl_seed_config(
            url="https://example.com", max_documents=0, max_depth=1, same_domain_only=False
        )


def test_build_crawl_seed_config_rejects_negative_depth():
    with pytest.raises(InvalidCrawlJobConfig):
        build_crawl_seed_config(
            url="https://example.com", max_documents=10, max_depth=-1, same_domain_only=False
        )


def test_build_crawl_seed_config_each_seed_independent_of_others():
    # The whole point of per-seed config: two seeds validated separately
    # keep their own max_documents/max_depth rather than sharing one.
    a = build_crawl_seed_config(
        url="https://a.example.com", max_documents=10, max_depth=0, same_domain_only=False
    )
    b = build_crawl_seed_config(
        url="https://b.example.com", max_documents=500, max_depth=5, same_domain_only=True
    )
    assert (a.max_documents, a.max_depth, a.same_domain_only) == (10, 0, False)
    assert (b.max_documents, b.max_depth, b.same_domain_only) == (500, 5, True)
