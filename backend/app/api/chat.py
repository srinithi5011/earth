from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message, User
from app.models.database import get_db
from app.schemas.chat import AnalyzeRequest, ChatRequest, ChatResponse
from app.services.conversation import empty_state
from app.services.rag import process_turn

router = APIRouter(tags=["chat"])
logger = logging.getLogger("darukaa.chat")


def _get_or_create_user(db: Session, session_id: str) -> User:
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user:
        user = User(session_id=session_id)
        db.add(user)
        db.flush()
    return user


def _get_or_create_conversation(
    db: Session, session_id: str, conversation_id: str | None
) -> Conversation:
    if conversation_id:
        convo = db.get(Conversation, conversation_id)
        if convo:
            return convo
    user = _get_or_create_user(db, session_id)
    convo = Conversation(user_id=user.id, session_id=session_id, environmental_context=empty_state())
    db.add(convo)
    db.flush()
    return convo


@router.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        convo = _get_or_create_conversation(db, payload.session_id, payload.conversation_id)

        db.add(Message(conversation_id=convo.id, role="user", content=payload.message))

        result = process_turn(
            db,
            message=payload.message,
            current_state=convo.environmental_context or empty_state(),
            structured_input=payload.structured_input,
        )

        convo.environmental_context = result["updated_state"]
        if result["recommendations"]:
            convo.previous_recommendations = (convo.previous_recommendations or []) + [
                r["recommendation"] for r in result["recommendations"]
            ]
        convo.retrieved_sources = (convo.retrieved_sources or []) + [
            e["chunk_id"] for e in result["evidence"]
        ]

        db.add(
            Message(
                conversation_id=convo.id,
                role="assistant",
                content=result["response"],
                structured_response=result,
            )
        )
        db.commit()

        return ChatResponse(
            conversation_id=convo.id,
            response=result["response"],
            needs_more_information=result["needs_more_information"],
            missing_fields=result["missing_fields"],
            environmental_assessment=result["environmental_assessment"],
            drivers=result["drivers"],
            relationships=result["relationships"],
            recommendations=result["recommendations"],
            evidence=result["evidence"],
            confidence=result["confidence"],
            demo_mode=result["demo_mode"],
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("chat endpoint failed")
        raise HTTPException(status_code=500, detail=f"Failed to process chat turn: {exc}") from exc


@router.post("/api/analyze", response_model=ChatResponse)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    """Structured-input-only endpoint: same pipeline, no conversation persistence required."""
    try:
        convo = _get_or_create_conversation(db, payload.session_id or "analyze-session", None)
        state = payload.environmental_state.model_dump()

        result = process_turn(db, message="", current_state=state, structured_input=state)
        convo.environmental_context = result["updated_state"]
        db.commit()

        return ChatResponse(
            conversation_id=convo.id,
            response=result["response"],
            needs_more_information=result["needs_more_information"],
            missing_fields=result["missing_fields"],
            environmental_assessment=result["environmental_assessment"],
            drivers=result["drivers"],
            relationships=result["relationships"],
            recommendations=result["recommendations"],
            evidence=result["evidence"],
            confidence=result["confidence"],
            demo_mode=result["demo_mode"],
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("analyze endpoint failed")
        raise HTTPException(status_code=500, detail=f"Failed to analyze state: {exc}") from exc


@router.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "conversation_id": convo.id,
        "environmental_context": convo.environmental_context,
        "previous_recommendations": convo.previous_recommendations,
        "retrieved_sources": convo.retrieved_sources,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in convo.messages
        ],
    }
