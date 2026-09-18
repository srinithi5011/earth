"""
Re-exports the embedding backend for the knowledge-ingestion layer.
The actual implementation lives in app/services/embeddings.py since it's
shared by both ingestion (knowledge/) and retrieval (services/).
"""
from app.services.embeddings import (  # noqa: F401
    TfidfEmbeddingBackend,
    cosine_similarity,
    get_embedding_backend,
)
