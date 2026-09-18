"""
Chunking strategy for the knowledge ingestion pipeline.

Uses a simple, dependency-free sliding-window chunker over sentences so
it works identically regardless of which embedding backend is active.
Chunk size and overlap are tunable; defaults are tuned for short-to-medium
scientific/report paragraphs (~120-220 words per chunk).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


@dataclass
class Chunk:
    index: int
    text: str


def split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = _SENTENCE_SPLIT_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(
    text: str,
    target_words: int = 160,
    overlap_sentences: int = 1,
) -> List[Chunk]:
    """
    Groups sentences into chunks of roughly `target_words` words each,
    carrying `overlap_sentences` sentences of overlap between consecutive
    chunks so retrieval doesn't lose context at chunk boundaries.
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: List[Chunk] = []
    current: List[str] = []
    current_words = 0
    idx = 0

    for sentence in sentences:
        words = len(sentence.split())
        if current and current_words + words > target_words:
            chunks.append(Chunk(index=idx, text=" ".join(current)))
            idx += 1
            # carry overlap
            current = current[-overlap_sentences:] if overlap_sentences else []
            current_words = sum(len(s.split()) for s in current)
        current.append(sentence)
        current_words += words

    if current:
        chunks.append(Chunk(index=idx, text=" ".join(current)))

    return chunks
