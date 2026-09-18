from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.knowledge.ingestion import ingest_document
from app.models.database import get_db
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument

router = APIRouter(tags=["evidence"])
logger = logging.getLogger("darukaa.evidence")


@router.get("/api/evidence")
def list_evidence(
    topic: Optional[str] = None,
    region: Optional[str] = None,
    organization: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Powers the Evidence Explorer page: browse ingested source chunks."""
    q = db.query(KnowledgeChunk)
    if topic:
        q = q.filter(KnowledgeChunk.topic == topic)
    if region:
        q = q.filter(KnowledgeChunk.region == region)
    if organization:
        q = q.filter(KnowledgeChunk.organization == organization)
    chunks = q.limit(limit).all()
    return [
        {
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "title": c.title,
            "organization": c.organization,
            "publication_year": c.publication_year,
            "topic": c.topic,
            "region": c.region,
            "document_type": c.document_type,
            "source_url": c.source_url,
            "credibility_tier": c.credibility_tier,
            "text": c.text,
        }
        for c in chunks
    ]


@router.get("/api/evidence/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(KnowledgeDocument).all()
    return [
        {
            "document_id": d.document_id,
            "title": d.title,
            "organization": d.organization,
            "authors": d.authors,
            "publication_year": d.publication_year,
            "source_url": d.source_url,
            "document_type": d.document_type,
            "topic": d.topic,
            "region": d.region,
            "tags": d.tags,
            "credibility_tier": d.credibility_tier,
        }
        for d in docs
    ]


@router.post("/api/knowledge/ingest")
async def ingest_knowledge(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    publication_year: Optional[int] = Form(None),
    source_url: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    region: Optional[str] = Form(None),
    credibility_tier: str = Form("user_supplied"),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "upload").suffix.lower()
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        doc = ingest_document(
            db,
            tmp_path,
            title=title,
            organization=organization,
            publication_year=publication_year,
            source_url=source_url,
            document_type=document_type,
            topic=topic,
            region=region,
            credibility_tier=credibility_tier,
        )
        db.commit()
        return {
            "document_id": doc.document_id,
            "title": doc.title,
            "chunks_created": db.query(KnowledgeChunk).filter(
                KnowledgeChunk.document_id == doc.document_id
            ).count(),
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True) if "tmp_path" in locals() else None
