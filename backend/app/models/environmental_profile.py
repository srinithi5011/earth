from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, JSON, String

from app.models.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class EnvironmentalProfile(Base):
    """
    Persisted snapshot of a structured environmental state, keyed so it
    can be re-attached to future conversations for the same
    session/user/location.
    """

    __tablename__ = "environmental_profiles"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, index=True, nullable=True)
    conversation_id = Column(String, index=True, nullable=True)

    region = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Full structured state (soil, land_use, crop, biodiversity, climate,
    # human_impact, location) stored as JSON — see
    # app/schemas/environment.py for the canonical shape.
    state = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
