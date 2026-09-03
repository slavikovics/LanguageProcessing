from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ips_user:ips_password@postgres:5432/ips"
    crawler_user_agent: str = "IPSLabBot/0.1 (+educational project)"
    crawler_politeness_delay_seconds: float = 1.0
    poll_interval_seconds: float = 3.0
    min_document_chars: int = 200
    links_per_page_cap: int = 50
