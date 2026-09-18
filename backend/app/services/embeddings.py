"""
Embedding service.

Default backend is TF-IDF (scikit-learn), which requires no network
access or model download — this keeps the project runnable fully
offline, which the spec requires ("must remain demonstrable even if
external LLM/API services fail").

The corpus vocabulary is fit once (on ingestion / seed) and persisted
so query-time vectorization is consistent with what was indexed. A
production deployment can swap EMBEDDING_MODEL to a real sentence
embedding model (e.g. an OpenAI/Voyage/local sentence-transformers
model) by implementing `SentenceEmbeddingBackend` below and switching
on `settings.EMBEDDING_MODEL` in `get_embedding_backend()`.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import List, Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.config import get_settings

settings = get_settings()

# backend/app/services/embeddings.py -> parents[3] is the repo root, so this
# resolves to <repo_root>/data/processed/tfidf_vectorizer.pkl regardless of
# current working directory (matches the top-level data/processed/ described
# in the project structure / README, and is shared by both the local-dev and
# containerized layouts since the Dockerfile copies data/ to /app/data/).
_REPO_ROOT_CANDIDATES = [
    Path(__file__).resolve().parents[3],  # local dev: backend/app/services/.. x3 -> repo root
    Path("/app"),  # container layout: backend contents ARE /app, data copied to /app/data
]
_VECTORIZER_PATH = next(
    (p / "data" / "processed" / "tfidf_vectorizer.pkl" for p in _REPO_ROOT_CANDIDATES if (p / "data").is_dir()),
    _REPO_ROOT_CANDIDATES[0] / "data" / "processed" / "tfidf_vectorizer.pkl",
)


class EmbeddingBackend(Protocol):
    def embed(self, texts: List[str]) -> List[List[float]]: ...
    def embed_query(self, text: str) -> List[float]: ...
    def dimension(self) -> int: ...


class TfidfEmbeddingBackend:
    """
    A real, working embedding backend with no external dependency.
    Fits a TF-IDF vectorizer over the full knowledge corpus and returns
    dense vectors (L2-normalized) so cosine similarity == dot product.
    """

    def __init__(self) -> None:
        self.vectorizer: TfidfVectorizer | None = None
        self._load()

    def _load(self) -> None:
        if _VECTORIZER_PATH.exists():
            with open(_VECTORIZER_PATH, "rb") as f:
                self.vectorizer = pickle.load(f)

    def _save(self) -> None:
        _VECTORIZER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_VECTORIZER_PATH, "wb") as f:
            pickle.dump(self.vectorizer, f)

    def fit(self, corpus_texts: List[str]) -> None:
        """Fit (or re-fit) the vectorizer over the full chunk corpus."""
        self.vectorizer = TfidfVectorizer(
            max_features=4096,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        self.vectorizer.fit(corpus_texts)
        self._save()

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self.vectorizer is None:
            self.fit(texts)
        matrix = self.vectorizer.transform(texts)
        dense = matrix.toarray()
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        dense = dense / norms
        return dense.tolist()

    def embed_query(self, text: str) -> List[float]:
        if self.vectorizer is None:
            raise RuntimeError(
                "Embedding vectorizer not fitted yet. Run scripts/seed.py or "
                "scripts/ingest.py first."
            )
        vec = self.vectorizer.transform([text]).toarray()[0]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def dimension(self) -> int:
        if self.vectorizer is None:
            return 0
        return len(self.vectorizer.get_feature_names_out())


_backend_singleton: TfidfEmbeddingBackend | None = None


def get_embedding_backend() -> TfidfEmbeddingBackend:
    global _backend_singleton
    if _backend_singleton is None:
        _backend_singleton = TfidfEmbeddingBackend()
    return _backend_singleton


def cosine_similarity(a: List[float], b: List[float]) -> float:
    va, vb = np.array(a), np.array(b)
    if va.shape != vb.shape or va.size == 0:
        return 0.0
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
