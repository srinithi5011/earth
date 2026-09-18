from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.database import get_db
from app.services.llm import is_demo_mode

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/api/health")
def health(db: Session = Depends(get_db)):
    db_ok = True
    db_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        db_error = str(exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "demo_mode": is_demo_mode(),
        "database_ok": db_ok,
        "database_error": db_error,
        "vector_backend": settings.VECTOR_BACKEND,
    }
