from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../secrets.env"), extra="ignore"
    )
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"
        ),
    )
    openrouter_api_key: str = ""
    openrouter_free_api_key: str = ""
    brevo_api_key: str = ""
    brevo_sender_email: str = ""
    brevo_sender_name: str = "Atlas"
    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dimensions: int = 1536
    openrouter_data_collection: str = "deny"
    openrouter_zdr: bool = False
    max_file_bytes: int = 25 * 1024 * 1024
    max_org_storage_bytes: int = 500 * 1024 * 1024
    max_org_documents: int = 200
    max_org_daily_questions: int = 200
    max_chunks: int = 8000
    ingestion_timeout_seconds: int = 1800
    parser_memory_limit_mb: int = 256
    worker_poll_seconds: int = 3
    run_worker: bool = False

    @property
    def configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_publishable_key)


@lru_cache
def settings() -> Settings:
    return Settings()
