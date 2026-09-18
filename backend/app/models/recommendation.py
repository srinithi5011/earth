from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text

from app.models.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)

    recommendation = Column(Text, nullable=False)
    scientific_reasoning = Column(Text, nullable=False)
    affected_metrics = Column(JSON, default=list)
    time_horizon = Column(JSON, default=dict)  # {short_term, medium_term, long_term}
    expected_effect = Column(JSON, default=dict)  # {metric: "increase"|"decrease"|"stabilize"}
    confidence = Column(Float, default=0.0)
    confidence_label = Column(String, default="Low")  # High | Medium | Low
    intervention_category = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class RecommendationEvidence(Base):
    __tablename__ = "recommendation_evidence"

    id = Column(String, primary_key=True, default=_uuid)
    recommendation_id = Column(String, ForeignKey("recommendations.id"), nullable=False)
    chunk_id = Column(String, nullable=False)

    title = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    relevance = Column(Float, default=0.0)
