#!/usr/bin/env python3
"""
CLI for ingesting a single document into the knowledge base.

Usage:
    python scripts/ingest.py path/to/file.pdf \\
        --title "..." --organization "..." --publication-year 2023 \\
        --source-url "https://..." --document-type report \\
        --topic soil --region "east africa" --credibility-tier authoritative
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_CONTAINER_APP_DIR = Path("/app")
if (_CONTAINER_APP_DIR / "app").is_dir():
    BACKEND_DIR = _CONTAINER_APP_DIR
else:
    BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.knowledge.ingestion import ingest_document  # noqa: E402
from app.models.database import Base, engine, session_scope  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a document into the Darukaa Earth knowledge base.")
    parser.add_argument("file_path")
    parser.add_argument("--title")
    parser.add_argument("--organization")
    parser.add_argument("--publication-year", type=int, dest="publication_year")
    parser.add_argument("--source-url", dest="source_url")
    parser.add_argument("--document-type", dest="document_type")
    parser.add_argument("--topic")
    parser.add_argument("--region")
    parser.add_argument("--credibility-tier", dest="credibility_tier", default="curated")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with session_scope() as db:
        doc = ingest_document(
            db,
            args.file_path,
            title=args.title,
            organization=args.organization,
            publication_year=args.publication_year,
            source_url=args.source_url,
            document_type=args.document_type,
            topic=args.topic,
            region=args.region,
            credibility_tier=args.credibility_tier,
        )
        print(f"Ingested document_id={doc.document_id} title={doc.title!r}")


if __name__ == "__main__":
    main()
