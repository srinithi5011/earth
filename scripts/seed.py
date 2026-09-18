#!/usr/bin/env python3
"""
Seeds the database with the curated knowledge corpus (data/seed/*.json)
and the environmental relationship graph (data/seed/relationships.json).

Usage:
    python scripts/seed.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Resolve paths for two layouts:
#  - local dev:      <repo_root>/scripts/seed.py, backend at <repo_root>/backend
#  - container:      /app/scripts_in_container/seed.py, backend app at /app (see Dockerfile)
_CONTAINER_APP_DIR = Path("/app")
if (_CONTAINER_APP_DIR / "app").is_dir():
    BACKEND_DIR = _CONTAINER_APP_DIR
    SEED_DIR = _CONTAINER_APP_DIR / "data" / "seed"
else:
    BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
    SEED_DIR = Path(__file__).resolve().parents[1] / "data" / "seed"

sys.path.insert(0, str(BACKEND_DIR))

from app.knowledge.chunking import chunk_text  # noqa: E402
from app.models.database import Base, engine, session_scope  # noqa: E402
from app.models.knowledge import (  # noqa: E402
    EnvironmentalRelationship,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.services.embeddings import get_embedding_backend  # noqa: E402
KNOWLEDGE_FILES = ["soil_health.json", "biodiversity.json", "climate.json", "human_impact.json"]


def seed_knowledge(db) -> int:
    total_chunks = 0
    existing = db.query(KnowledgeDocument).count()
    if existing > 0:
        print(f"Knowledge documents already present ({existing}). Skipping document seed.")
    else:
        for filename in KNOWLEDGE_FILES:
            path = SEED_DIR / filename
            records = json.loads(path.read_text(encoding="utf-8"))
            for rec in records:
                doc = KnowledgeDocument(
                    title=rec["title"],
                    organization=rec.get("organization"),
                    authors=rec.get("authors"),
                    publication_year=rec.get("publication_year"),
                    source_url=rec.get("source_url"),
                    document_type=rec.get("document_type"),
                    topic=rec.get("topic"),
                    region=rec.get("region"),
                    tags=rec.get("tags"),
                    credibility_tier=rec.get("credibility_tier", "curated"),
                    raw_text=rec["text"],
                )
                db.add(doc)
                db.flush()

                chunks = chunk_text(rec["text"])
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
                    total_chunks += 1
            print(f"Seeded {len(records)} documents from {filename}")
        db.flush()

    # Embed everything (idempotent — re-fits vocabulary over full corpus)
    all_chunks = db.query(KnowledgeChunk).all()
    if all_chunks:
        texts = [c.text for c in all_chunks]
        backend = get_embedding_backend()
        backend.fit(texts)
        vectors = backend.embed(texts)
        for chunk, vec in zip(all_chunks, vectors):
            chunk.embedding = vec
        db.flush()
        print(f"Embedded {len(all_chunks)} knowledge chunks (TF-IDF, dim={backend.dimension()})")

    return total_chunks


def seed_relationships(db) -> int:
    existing = db.query(EnvironmentalRelationship).count()
    if existing > 0:
        print(f"Relationships already present ({existing}). Skipping.")
        return existing

    path = SEED_DIR / "relationships.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    for rec in records:
        db.add(EnvironmentalRelationship(**rec))
    db.flush()
    print(f"Seeded {len(records)} environmental relationships")
    return len(records)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with session_scope() as db:
        seed_knowledge(db)
        seed_relationships(db)
    print("Seeding complete.")


if __name__ == "__main__":
    main()
