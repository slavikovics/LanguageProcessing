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
    speech_stream_max_concurrency: int = 4
    """Caps how many live-STT chunks (/speech/stt/stream) this api process
    will have in flight against speech-service at once — that container's
    cpus= budget (docker-compose.yml) is shared across every open ambient-
    listening/dictation session, not just one. The app now routinely has
    more than one live session open together (the always-on ambient mic
    plus a push-to-talk VoiceInputButton on whatever page is open, plus
    Settings' own STT preview) — 2 was observed being exceeded in ordinary
    use (3 concurrent /speech/stt/stream connections queuing behind only 2
    semaphore slots), and the resulting extra per-chunk latency is a
    plausible contributor to occasional client-side "connection lost"
    reports. 4 matches the stream model's WHISPER_CPU_THREADS=2 against this
    container's cpus=4.0 budget (docker-compose.yml) — two chunks can
    actually run in parallel without over-subscribing the CPU, and the rest
    just queue a bit longer instead of each other."""
    crawler_user_agent: str = "IPSLabBot/0.1 (+educational project)"
    cors_allow_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
