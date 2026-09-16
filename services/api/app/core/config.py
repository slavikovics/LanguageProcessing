from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ips_user:ips_password@postgres:5432/ips"
    nlp_service_url: str = "http://nlp-service:8001"
    lang_id_service_url: str = "http://lang-id-service:8002"
    summarization_service_url: str = "http://summarization-service:8003"
    speech_service_url: str = "http://speech-service:8004"
    crawl_progress_poll_interval_seconds: float = 0.7
    # 4 matches WHISPER_CPU_THREADS=2 against speech-service's cpus=4.0 budget (docker-compose.yml).
    speech_stream_max_concurrency: int = 4
    crawler_user_agent: str = "IPSLabBot/0.1 (+educational project)"
    cors_allow_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
