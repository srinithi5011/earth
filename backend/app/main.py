from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, environment, evidence, health, relationships
from app.config import get_settings
from app.models.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("darukaa")

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Evidence-grounded environmental intelligence system. RAG + deterministic "
        "multi-metric reasoning + evidence-verified recommendations."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    try:
        init_db()
        logger.info("Database initialized (%s)", settings.DATABASE_URL)
    except Exception:
        logger.exception("Database initialization failed")
        raise


app.include_router(health.router)
app.include_router(chat.router)
app.include_router(environment.router)
app.include_router(evidence.router)
app.include_router(relationships.router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "health": "/api/health",
    }
