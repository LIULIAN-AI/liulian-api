"""Runtime configuration for liulian-api.

Per ADR 0003 (TimescaleDB), Day-1 sprint uses plain Postgres; TimescaleDB
extension is enabled after M1 demo ships. Per ADR 0009 (Spring Boot →
FastAPI), the env-var vocabulary mirrors neobanker for operator continuity.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, BeforeValidator, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [item.strip() for item in value.split(',') if item.strip()]


class Settings(BaseSettings):
    """All runtime config; one env var per field; no profile bloat."""

    model_config = SettingsConfigDict(
        env_prefix='LIULIAN_API_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    env: str = Field('dev', description='dev | staging | prod')
    log_level: str = 'INFO'

    # Database
    database_url: PostgresDsn = Field(
        'postgresql+asyncpg://liulian:liulian@localhost:5432/liulian_api',
        description='SQLAlchemy/asyncpg URL.',
    )

    # Cache + queue
    redis_url: str = 'redis://localhost:6379/0'

    # Object storage
    minio_endpoint: str = 'localhost:9000'
    minio_access_key: str = 'minioadmin'
    minio_secret_key: str = 'minioadmin'
    minio_bucket: str = 'liulian-artifacts'
    minio_secure: bool = False

    # Agent service (separate repo; HTTP between two FastAPI services)
    agent_base_url: AnyHttpUrl = Field('http://localhost:8001')

    # Auth (Day-1 uses bearer-token stub; Clerk wired at M2+)
    demo_token: str = 'demo-only-not-for-production'

    # CORS (env name mirrors neobanker convention; see ADR 0009)
    cors_allowed_origins: Annotated[list[str], BeforeValidator(_split_csv)] = Field(
        default_factory=lambda: ['http://localhost:3000', 'http://localhost:8080']
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
