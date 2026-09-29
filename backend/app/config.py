"""
Application configuration management.
Loads settings from environment variables with validation.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "digital-marketing-ai"
    app_env: str = "development"
    app_debug: bool = True
    app_version: str = "0.1.0"
    secret_key: str = "dev-secret-key-change-in-production"
    encryption_key: str = "0123456789abcdef0123456789abcdef"

    # ── PostgreSQL ──
    database_url: str = "postgresql+asyncpg://marketing_ai_user:devpassword@localhost:5432/marketing_ai"
    database_url_sync: str = "postgresql://marketing_ai_user:devpassword@localhost:5432/marketing_ai"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Qdrant ──
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # ── MinIO ──
    minio_host: str = "localhost"
    minio_port: int = 9000
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_default_bucket: str = "artifacts"
    minio_secure: bool = False

    # ── Ollama ──
    ollama_base_url: str = "http://localhost:11434"
    boss_agent_model: str = "llama3.2:3b-instruct-q4_K_M"
    sub_agent_model: str = "llama3.2:1b-instruct-q4_K_M"
    fallback_model: str = "llama3.2:1b-instruct-q4_K_M"
    embedding_model: str = "nomic-embed-text"

    # ── JWT Auth ──
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── API ──
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── Celery ──
    celery_worker_concurrency: int = 2
    celery_task_soft_time_limit: int = 600
    celery_task_time_limit: int = 900

    # ── Rate Limiting ──
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 500
    max_concurrent_tasks_per_user: int = 5

    # ── Logging ──
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "logs/app.log"

    # ── Frontend ──
    frontend_url: str = "http://localhost:3000"

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def set_jwt_secret(cls, v, info):
        """Fall back to secret_key if jwt_secret_key not set."""
        return v or info.data.get("secret_key", "dev-secret")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def minio_endpoint(self) -> str:
        return f"{self.minio_host}:{self.minio_port}"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
