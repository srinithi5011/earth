from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text

from app.models.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    document_id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    organization = Column(String, nullable=True)
    authors = Column(JSON, nullable=True)  # list[str], nullable if unavailable
    publication_year = Column(Integer, nullable=True)
    source_url = Column(String, nullable=True)
    document_type = Column(String, nullable=True)  # report | dataset | paper | curated_summary
    topic = Column(String, nullable=True)  # soil | biodiversity | climate | human_impact | land_use
    region = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)  # list[str]
    credibility_tier = Column(String, default="curated")  # authoritative | peer_reviewed | curated | user_supplied
    raw_text = Column(Text, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    chunk_id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)

    # Denormalized metadata copied from the parent document to make
    # metadata filtering fast without a join, per the required schema.
    title = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    publication_year = Column(Integer, nullable=True)
    source_url = Column(String, nullable=True)
    document_type = Column(String, nullable=True)
    topic = Column(String, nullable=True)
    region = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    credibility_tier = Column(String, default="curated")

    # Embedding vector. On Postgres this column is created as
    # `vector(N)` by database/init.sql and accessed via pgvector's
    # cosine operator; on SQLite it's a JSON-encoded float list and
    # search happens in-process (see app/services/retrieval.py).
    embedding = Column(JSON, nullable=True)


class EnvironmentalRelationship(Base):
    """
    The structured environmental knowledge-graph edges used by the
    deterministic reasoning engine (app/services/reasoning.py). Each row
    is one causal/associative relationship the LLM is NOT allowed to
    invent on its own — it can only combine relationships that exist
    here with the user's environmental state and retrieved evidence.
    """

    __tablename__ = "environmental_relationships"

    id = Column(String, primary_key=True, default=_uuid)
    source_metric = Column(String, nullable=False, index=True)
    relationship = Column(String, nullable=False)  # e.g. "increases", "reduces"
    target_metric = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=False)  # "positive" | "negative"
    strength = Column(String, default="moderate")  # weak | moderate | strong
    scientific_basis = Column(Text, nullable=True)
    source_document_id = Column(String, nullable=True)
