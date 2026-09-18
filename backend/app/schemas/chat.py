from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.environment import EnvironmentalState


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client-generated session identifier")
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    # Optional structured input, merged on top of natural-language extraction.
    structured_input: Optional[Dict[str, Any]] = None


class EvidenceItem(BaseModel):
    chunk_id: str
    title: Optional[str] = None
    organization: Optional[str] = None
    source_url: Optional[str] = None
    publication_year: Optional[int] = None
    document_type: Optional[str] = None
    relevance: float = 0.0
    text_snippet: Optional[str] = None


class TimeHorizon(BaseModel):
    short_term: Optional[str] = None
    medium_term: Optional[str] = None
    long_term: Optional[str] = None


class RecommendationOut(BaseModel):
    recommendation: str
    scientific_reasoning: str
    affected_metrics: List[str] = []
    time_horizon: TimeHorizon = TimeHorizon()
    expected_effect: Dict[str, str] = {}
    confidence: float = 0.0
    confidence_label: str = "Low"
    evidence: List[EvidenceItem] = []


class RelationshipEdge(BaseModel):
    source_metric: str
    relationship: str
    target_metric: str
    direction: str
    strength: str


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    needs_more_information: bool = False
    missing_fields: List[str] = []
    environmental_assessment: Dict[str, Any] = {}
    drivers: List[str] = []
    relationships: List[RelationshipEdge] = []
    recommendations: List[RecommendationOut] = []
    evidence: List[EvidenceItem] = []
    confidence: float = 0.0
    demo_mode: bool = False


class AnalyzeRequest(BaseModel):
    """Structured-input-only variant of /api/chat, for programmatic use."""

    environmental_state: EnvironmentalState
    session_id: Optional[str] = "analyze-session"
