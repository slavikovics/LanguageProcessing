from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ips_user:ips_password@postgres:5432/ips"
    crawler_user_agent: str = "IPSLabBot/0.1 (+educational project)"
    crawler_politeness_delay_seconds: float = 1.0
    poll_interval_seconds: float = 3.0
    min_document_chars: int = 200
    links_per_page_cap: int = 50
    # How many crawl_jobs run at once — jobs on different domains (e.g. the
    # several seeds of one run_collection_crawl) don't have to wait for each
    # other just because the worker only ever looked at one at a time.
    max_concurrent_jobs: int = 4
    # How many URLs one job fetches in parallel. DomainThrottle still
    # serializes requests to the *same* domain (politeness is per-domain,
    # not per-job), so this mainly overlaps one page's parsing/DB writes
    # with the next page's network wait, and lets a job with links across
    # several hosts actually use them concurrently.
    max_concurrent_fetches_per_job: int = 5
