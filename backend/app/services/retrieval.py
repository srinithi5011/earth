"""
Retrieval service.

Implements: embedding-based similarity search, metadata filtering,
similarity threshold, source ranking, duplicate removal, and context
compression -- the retrieval half of the RAG pipeline described in the
spec (section 6).

On SQLite this runs an in-process cosine-similarity scan over chunk
embeddings (fine at hackathon/demo scale). On Postgres + pgvector
(production path), the same interface should be backed by a native
`ORDER BY embedding <=> query_vector` query -- see
`database/init.sql` for the pgvector index definition; swapping the
`_search_sqlite` implementation below for a pgvector query is the only
change required, the rest of the RAG pipeline is unaffected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.knowledge import KnowledgeChunk
from app.services.embeddings import cosine_similarity, get_embedding_backend

settings = get_settings()


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    title: Optional[str]
    organization: Optional[str]
    source_url: Optional[str]
    publication_year: Optional[int]
    document_type: Optional[str]
    topic: Optional[str]
    region: Optional[str]
    credibility_tier: str
    similarity: float
    relevance: float = 0.0  # similarity blended with credibility (evidence ranking)


_CREDIBILITY_WEIGHT = {
    "authoritative": 1.0,
    "peer_reviewed": 0.95,
    "curated": 0.75,
    "user_supplied": 0.55,
}


def _blend_relevance(similarity: float, credibility_tier: str) -> float:
    weight = _CREDIBILITY_WEIGHT.get(credibility_tier, 0.7)
    # Similarity dominates, credibility nudges ranking among close scores.
    return round(min(1.0, similarity * 0.8 + weight * 0.2), 4)


def retrieve(
    db: Session,
    query: str,
    *,
    top_k: Optional[int] = None,
    topic: Optional[str] = None,
    region: Optional[str] = None,
    similarity_threshold: Optional[float] = None,
) -> List[RetrievedChunk]:
    """
    Runs embedding generation -> vector search -> metadata filtering ->
    similarity threshold -> duplicate removal -> evidence ranking, and
    returns the top_k most relevant, deduplicated chunks.
    """
    top_k = top_k or settings.RETRIEVAL_TOP_K
    threshold = (
        similarity_threshold
        if similarity_threshold is not None
        else settings.RETRIEVAL_SIMILARITY_THRESHOLD
    )

    backend = get_embedding_backend()
    if backend.vectorizer is None:
        return []  # knowledge base not yet indexed

    query_vector = backend.embed_query(query)

    q = db.query(KnowledgeChunk).filter(KnowledgeChunk.embedding.isnot(None))
    if topic:
        q = q.filter(KnowledgeChunk.topic == topic)
    if region:
        q = q.filter((KnowledgeChunk.region == region) | (KnowledgeChunk.region.is_(None)))
    candidates = q.all()

    scored: List[RetrievedChunk] = []
    for c in candidates:
        sim = cosine_similarity(query_vector, c.embedding or [])
        if sim < threshold:
            continue
        scored.append(
            RetrievedChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                text=c.text,
                title=c.title,
                organization=c.organization,
                source_url=c.source_url,
                publication_year=c.publication_year,
                document_type=c.document_type,
                topic=c.topic,
                region=c.region,
                credibility_tier=c.credibility_tier or "curated",
                similarity=round(sim, 4),
            )
        )

    # Evidence ranking: blend similarity with source credibility.
    for r in scored:
        r.relevance = _blend_relevance(r.similarity, r.credibility_tier)
    scored.sort(key=lambda r: r.relevance, reverse=True)

    # Duplicate removal: collapse near-duplicate chunks from the same
    # document (keep the highest-relevance chunk per document, unless
    # the document contributes multiple distinct high-value chunks —
    # here we cap at 2 chunks per document to preserve source diversity).
    deduped: List[RetrievedChunk] = []
    per_document_count: dict[str, int] = {}
    seen_text_prefixes: set[str] = set()
    for r in scored:
        prefix = r.text[:80].lower()
        if prefix in seen_text_prefixes:
            continue
        count = per_document_count.get(r.document_id, 0)
        if count >= 2:
            continue
        deduped.append(r)
        seen_text_prefixes.add(prefix)
        per_document_count[r.document_id] = count + 1
        if len(deduped) >= top_k:
            break

    return deduped


def compress_context(chunks: List[RetrievedChunk], max_chars_per_chunk: int = 500) -> List[RetrievedChunk]:
    """Context compression: trims each chunk's text for prompt budget."""
    compressed = []
    for c in chunks:
        text = c.text if len(c.text) <= max_chars_per_chunk else c.text[:max_chars_per_chunk].rsplit(" ", 1)[0] + "…"
        compressed.append(
            RetrievedChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                text=text,
                title=c.title,
                organization=c.organization,
                source_url=c.source_url,
                publication_year=c.publication_year,
                document_type=c.document_type,
                topic=c.topic,
                region=c.region,
                credibility_tier=c.credibility_tier,
                similarity=c.similarity,
                relevance=c.relevance,
            )
        )
    return compressed
