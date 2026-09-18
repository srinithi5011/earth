"""
SQLAlchemy engine + session management.

Works against SQLite out of the box (zero-infra local/demo mode) and
against PostgreSQL + pgvector when DATABASE_URL points at Postgres
(the docker-compose / production path). The ORM models avoid any
Postgres-only column types so the same models work on both backends;
the pgvector `vector` column is created separately via
`database/init.sql` for the Postgres path, and knowledge_chunks falls
back to a JSON-encoded float array + in-process TF-IDF/cosine search
on SQLite (see app/services/retrieval.py).
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Create all tables. Idempotent."""
    from app.models import (  # noqa: F401  (ensure models are registered)
        conversation,
        environmental_profile,
        knowledge,
        recommendation,
    )

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    """FastAPI dependency: yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Context manager for scripts (ingestion, seeding, evaluation)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
