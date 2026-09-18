"""
Knowledge ingestion pipeline.

Accepts PDF, TXT, MD, CSV, JSON (and URL *metadata*, i.e. a JSON record
describing a document already fetched elsewhere — this project does not
fetch arbitrary external URLs at ingestion time since network access
cannot be assumed in every deployment environment).

Pipeline: read -> extract text -> chunk -> embed -> persist (document +
chunks with vectors) -> re-fit the shared TF-IDF vocabulary over the
full corpus so every chunk's vector stays comparable.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.knowledge.chunking import chunk_text
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.embeddings import get_embedding_backend

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json"}


def _extract_text_from_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "pypdf is required to ingest PDF files. Install it via "
            "backend/requirements.txt."
        ) from exc
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_text_from_csv(path: Path) -> str:
    lines = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        for row in reader:
            pairs = ", ".join(f"{h}: {v}" for h, v in zip(header, row))
            lines.append(pairs)
    return "\n".join(lines)


def _extract_document_and_text(path: Path) -> tuple[Dict[str, Any], str]:
    """
    Returns (metadata, text). For JSON inputs, metadata fields
    (title/organization/authors/...) may be embedded directly in the
    file; for other formats, metadata falls back to filename-derived
    defaults and should be supplied by the caller.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return {}, _extract_text_from_pdf(path)
    if suffix in (".txt", ".md"):
        return {}, path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".csv":
        return {}, _extract_text_from_csv(path)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = payload.get("text", "")
        meta = {k: v for k, v in payload.items() if k != "text"}
        return meta, text
    raise ValueError(f"Unsupported file type: {suffix}")


def ingest_document(
    db: Session,
    file_path: str,
    *,
    title: Optional[str] = None,
    organization: Optional[str] = None,
    authors: Optional[List[str]] = None,
    publication_year: Optional[int] = None,
    source_url: Optional[str] = None,
    document_type: Optional[str] = None,
    topic: Optional[str] = None,
    region: Optional[str] = None,
    tags: Optional[List[str]] = None,
    credibility_tier: str = "curated",
) -> KnowledgeDocument:
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    meta_from_file, text = _extract_document_and_text(path)
    if not text or not text.strip():
        raise ValueError(f"No extractable text found in {file_path}")

    doc = KnowledgeDocument(
        title=title or meta_from_file.get("title") or path.stem,
        organization=organization or meta_from_file.get("organization"),
        authors=authors or meta_from_file.get("authors"),
        publication_year=publication_year or meta_from_file.get("publication_year"),
        source_url=source_url or meta_from_file.get("source_url"),
        document_type=document_type or meta_from_file.get("document_type") or "document",
        topic=topic or meta_from_file.get("topic"),
        region=region or meta_from_file.get("region"),
        tags=tags or meta_from_file.get("tags") or [],
        credibility_tier=credibility_tier,
        raw_text=text,
    )
    db.add(doc)
    db.flush()  # assigns document_id

    chunks = chunk_text(text)
    for c in chunks:
        db.add(
            KnowledgeChunk(
                document_id=doc.document_id,
                chunk_index=c.index,
                text=c.text,
                title=doc.title,
                organization=doc.organization,
                publication_year=doc.publication_year,
                source_url=doc.source_url,
                document_type=doc.document_type,
                topic=doc.topic,
                region=doc.region,
                tags=doc.tags,
                credibility_tier=doc.credibility_tier,
            )
        )
    db.flush()

    reindex_all_embeddings(db)
    return doc


def reindex_all_embeddings(db: Session) -> int:
    """
    Re-fits the shared TF-IDF vocabulary over every chunk currently in
    the database, then re-embeds every chunk so all vectors stay in the
    same vector space. Returns the number of chunks embedded.
    """
    all_chunks: List[KnowledgeChunk] = db.query(KnowledgeChunk).all()
    if not all_chunks:
        return 0
    texts = [c.text for c in all_chunks]
    backend = get_embedding_backend()
    backend.fit(texts)
    vectors = backend.embed(texts)
    for chunk, vec in zip(all_chunks, vectors):
        chunk.embedding = vec
    db.flush()
    return len(all_chunks)
