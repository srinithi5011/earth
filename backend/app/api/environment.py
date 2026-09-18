from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.environmental_profile import EnvironmentalProfile
from app.schemas.environment import EnvironmentalState

router = APIRouter(tags=["environment"])
logger = logging.getLogger("darukaa.environment")


@router.post("/api/environment")
def create_or_update_environment(
    state: EnvironmentalState,
    session_id: str | None = None,
    conversation_id: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        profile = EnvironmentalProfile(
            session_id=session_id,
            conversation_id=conversation_id,
            region=state.location.region,
            latitude=state.location.latitude,
            longitude=state.location.longitude,
            state=state.model_dump(),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return {"profile_id": profile.id, "state": profile.state}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("failed to save environmental profile")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/environment/{profile_id}")
def get_environment(profile_id: str, db: Session = Depends(get_db)):
    profile = db.get(EnvironmentalProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Environmental profile not found")
    return {
        "profile_id": profile.id,
        "region": profile.region,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "state": profile.state,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }
