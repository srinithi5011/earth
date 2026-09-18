"""
LLM service.

Provider is selected via LLM_PROVIDER / LLM_API_KEY / LLM_MODEL env vars
-- never hard-coded. When DEMO_MODE=true (default, and automatically
forced on if no LLM_API_KEY is configured), the system runs entirely on
deterministic templates driven by the reasoning engine's output, so the
app stays demonstrable with zero external services, per spec section 29.

The LLM is used ONLY for phrasing/synthesis, never for inventing facts:
it is passed nothing but data already produced by the deterministic
reasoning engine and the retrieval layer, and prompts explicitly forbid
introducing new claims, sources, or numbers.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.config import get_settings

settings = get_settings()


class LLMUnavailableError(Exception):
    pass


def is_demo_mode() -> bool:
    return settings.DEMO_MODE or not settings.LLM_API_KEY


def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise LLMUnavailableError("anthropic SDK not installed") from exc
    try:
        client = anthropic.Anthropic(api_key=settings.LLM_API_KEY)
        resp = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=1200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
    except Exception as exc:  # network failure, auth failure, rate limit, etc.
        raise LLMUnavailableError(str(exc)) from exc


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    try:
        import openai
    except ImportError as exc:
        raise LLMUnavailableError("openai SDK not installed") from exc
    try:
        client = openai.OpenAI(api_key=settings.LLM_API_KEY)
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1200,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        raise LLMUnavailableError(str(exc)) from exc


def generate(system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    Returns the LLM's raw text, or None if the LLM is unavailable/disabled
    -- callers MUST handle None by falling back to deterministic templates
    (see app/services/recommendations.py), never by crashing.
    """
    if is_demo_mode():
        return None
    try:
        if settings.LLM_PROVIDER == "anthropic":
            return _call_anthropic(system_prompt, user_prompt)
        if settings.LLM_PROVIDER == "openai":
            return _call_openai(system_prompt, user_prompt)
        return None
    except LLMUnavailableError:
        return None


def generate_json(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Same as generate(), but parses the result as JSON. Returns None on
    unavailability OR malformed JSON -- callers must have a deterministic
    fallback in both cases."""
    raw = generate(system_prompt, user_prompt)
    if raw is None:
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None
