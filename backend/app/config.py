"""
Application configuration.

All configuration is sourced from environment variables. Nothing is
hard-coded. See .env.example at the repo root for the full list of
supported variables.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:  # pydantic v1 fallback
    from pydantic import BaseSettings, Field  # type: ignore


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Darukaa Earth — AI Biodiversity Intelligence"
    ENV: str = Field(default="development")
    DEMO_MODE: bool = Field(default=True)
    FRONTEND_URL: str = Field(default="http://localhost:5173")

    # --- Database ---
    # Defaults to a local SQLite file so the project runs with zero
    # external infrastructure. In docker-compose / production this is
    # overridden to the Postgres + pgvector connection string.
    DATABASE_URL: str = Field(
        default="sqlite:///./data/darukaa.db"
    )
    VECTOR_BACKEND: str = Field(default="sqlite_tfidf")  # sqlite_tfidf | pgvector | chroma

    # --- LLM ---
    LLM_PROVIDER: str = Field(default="anthropic")  # anthropic | openai | none
    LLM_API_KEY: Optional[str] = Field(default=None)
    LLM_MODEL: str = Field(default="claude-sonnet-4-6")

    # --- Embeddings ---
    # "tfidf" requires no network/model download and is used as the
    # offline-safe default. Set to an embedding model name to use a real
    # sentence embedding model when one is available in the deployment
    # environment.
    EMBEDDING_MODEL: str = Field(default="tfidf")

    # --- Retrieval ---
    RETRIEVAL_TOP_K: int = Field(default=6)
    RETRIEVAL_SIMILARITY_THRESHOLD: float = Field(default=0.08)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
