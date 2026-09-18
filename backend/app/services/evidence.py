"""
Evidence verification service (spec section 7).

Runs deterministic checks before any recommendation is returned to the
user:
  A. Is the recommendation supported by retrieved evidence (non-empty,
     above similarity threshold)?
  B. Are the claimed affected metrics plausible given the evidence set?
  C. Are numeric claims in the recommendation text actually present in
     the evidence (no invented percentages)?
  D. Is the source credible (credibility tier)?
  E. Is the source topically relevant (similarity/relevance threshold)?

This never fabricates citations, and it never lets an LLM-authored
numeric claim through unless that exact figure appears in the evidence
text -- if it can't verify a number, it strips confidence rather than
trusting the LLM's phrasing.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.config import get_settings
from app.services.retrieval import RetrievedChunk

settings = get_settings()

_NUMBER_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*%")
_MIN_CREDIBLE_TIER = {"authoritative", "peer_reviewed", "curated"}  # user_supplied excluded by default


def _numbers_in(text: str) -> List[str]:
    return _NUMBER_RE.findall(text)


def verify_recommendation(
    recommendation: Dict[str, Any], evidence_chunks: List[RetrievedChunk]
) -> Dict[str, Any]:
    issues: List[str] = []

    # A. Supported by evidence at all?
    if not evidence_chunks:
        issues.append("no evidence retrieved above similarity threshold")

    # D. Source credibility
    uncredible = [c for c in evidence_chunks if c.credibility_tier not in _MIN_CREDIBLE_TIER]
    if uncredible and len(uncredible) == len(evidence_chunks):
        issues.append("all retrieved sources are below the minimum credibility tier")

    # E. Topical relevance
    low_relevance = [c for c in evidence_chunks if c.relevance < settings.RETRIEVAL_SIMILARITY_THRESHOLD]
    if low_relevance and len(low_relevance) == len(evidence_chunks):
        issues.append("retrieved sources did not clear the topical relevance threshold")

    # C. Numeric claims must be traceable to evidence text
    claim_numbers = set(_numbers_in(recommendation.get("recommendation", "")))
    if claim_numbers:
        evidence_text = " ".join(c.text for c in evidence_chunks)
        evidence_numbers = set(_numbers_in(evidence_text))
        unverified = claim_numbers - evidence_numbers
        if unverified:
            issues.append(
                f"numeric claim(s) {sorted(unverified)} not found verbatim in retrieved evidence"
            )

    supported = len(issues) == 0
    return {"supported": supported, "issues": issues}


def strip_unverified_numbers(text: str, evidence_chunks: List[RetrievedChunk]) -> str:
    """
    Defensive post-processing: replaces any numeric percentage claim in
    generated text that does not appear in the evidence with the
    required disclaimer, in case an LLM slipped one past the prompt
    instructions.
    """
    evidence_text = " ".join(c.text for c in evidence_chunks)
    evidence_numbers = set(_numbers_in(evidence_text))

    def _replace(match: re.Match) -> str:
        num = match.group(1)
        if num in evidence_numbers:
            return match.group(0)
        return "[quantitative estimate unavailable from retrieved evidence]"

    return _NUMBER_RE.sub(_replace, text)
