from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.knowledge import EnvironmentalRelationship

router = APIRouter(tags=["relationships"])


@router.get("/api/relationships")
def list_relationships(db: Session = Depends(get_db)):
    """Powers the Reasoning Graph page: the full relationship knowledge graph."""
    edges = db.query(EnvironmentalRelationship).all()
    return [
        {
            "source_metric": e.source_metric,
            "relationship": e.relationship,
            "target_metric": e.target_metric,
            "direction": e.direction,
            "strength": e.strength,
            "scientific_basis": e.scientific_basis,
        }
        for e in edges
    ]
