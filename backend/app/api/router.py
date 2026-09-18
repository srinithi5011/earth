from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.models.database import get_db
from app.services.rag import process_turn

router = APIRouter(prefix="/api", tags=["Environmental Analysis & Chat"])


# --- Schemas ---

class StructuredInput(BaseModel):
    soil: Optional[Dict[str, Any]] = None
    climate: Optional[Dict[str, Any]] = None
    biodiversity: Optional[Dict[str, Any]] = None
    human_impact: Optional[Dict[str, Any]] = None
    land_use: Optional[str] = None
    crop: Optional[str] = None
    location: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or description of the ecosystem state")
    session_id: str = Field(..., description="Unique session identifier")
    conversation_id: Optional[str] = Field(None, description="Existing conversation UUID if continuing a session")
    structured_input: Optional[StructuredInput] = Field(None, description="Explicit structured environmental metrics")


class AnalysisRequest(BaseModel):
    message: str = Field(..., description="Text description of the land or degraded ecosystem")
    structured_input: Optional[StructuredInput] = Field(None, description="Structured environmental data")


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    needs_more_information: bool
    missing_fields: List[str]
    environmental_assessment: Dict[str, Any]
    drivers: List[str]
    relationships: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    confidence: float
    updated_state: Dict[str, Any]
    demo_mode: bool


# --- Endpoints ---

@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat_turn(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Stateful multi-turn conversation endpoint. Retrieves existing environmental context,
    runs the multi-metric reasoning pipeline, and persists conversation logs.
    """
    # Retrieve or create conversation record
    conversation = None
    if payload.conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()

    if not conversation:
        conversation = Conversation(
            session_id=payload.session_id,
            environmental_context={},
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)

    # Execute RAG & Reasoning Pipeline
    structured_dict = payload.structured_input.model_dump(exclude_none=True) if payload.structured_input else None
    
    turn_output = process_turn(
        db=db,
        message=payload.message,
        current_state=conversation.environmental_context or {},
        structured_input=structured_dict,
    )

    # Update conversation state with merged environmental context
    conversation.environmental_context = turn_output["updated_state"]

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=turn_output["response"],
        structured_response=turn_output,
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "conversation_id": conversation.id,
        **turn_output
    }


@router.post("/analyze", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
def analyze_environment(payload: AnalysisRequest, db: Session = Depends(get_db)):
    """
    Stateless single-turn analysis endpoint. Directly executes environmental assessment 
    without tracking session message history.
    """
    structured_dict = payload.structured_input.model_dump(exclude_none=True) if payload.structured_input else None
    
    turn_output = process_turn(
        db=db,
        message=payload.message,
        current_state={},
        structured_input=structured_dict,
    )
    
    return turn_output