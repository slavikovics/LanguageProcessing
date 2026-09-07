from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ips_user:ips_password@postgres:5432/ips"
    nlp_service_url: str = "http://nlp-service:8001"
    lang_id_service_url: str = "http://lang-id-service:8002"
    crawl_progress_poll_interval_seconds: float = 0.7
    # Same env var and default crawler-service reads — sites like Wikipedia
    # 403 a bare/default httpx User-Agent, so ad-hoc URL classification
    # needs the same descriptive one the crawler already uses successfully.
    crawler_user_agent: str = "IPSLabBot/0.1 (+educational project)"
    cors_allow_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
