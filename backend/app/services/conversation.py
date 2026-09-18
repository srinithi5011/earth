"""
Conversation + environmental-state-extraction service.

Handles:
- Merging structured JSON input into the environmental state.
- Extracting environmental variables from natural language via
  regex/keyword rules (a fast, deterministic, offline-safe first pass;
  see `llm.py` for the optional LLM-assisted extraction path used when
  DEMO_MODE=false and an LLM_API_KEY is configured).
- Missing-information detection against CORE_FIELDS / ALL_TRACKED_FIELDS.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.environment import (
    ALL_TRACKED_FIELDS,
    CORE_FIELDS,
    FIELD_QUESTIONS,
    EnvironmentalState,
)

# --- Natural language extraction patterns -----------------------------

_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("soil.organic_carbon", re.compile(r"(?:soil\s+)?organic\s+carbon(?:\s+is|\s*[:=])?\s*(\d+(?:\.\d+)?)\s*%?", re.I)),
    ("soil.ph", re.compile(r"\bph\s*(?:is|of|[:=])?\s*(\d+(?:\.\d+)?)", re.I)),
    ("soil.moisture", re.compile(r"soil\s+moisture(?:\s+is|\s*[:=])?\s*(\d+(?:\.\d+)?)\s*%?", re.I)),
    ("climate.rainfall_num", re.compile(r"rainfall(?:\s+is|\s*[:=])?\s*(\d+(?:\.\d+)?)\s*mm", re.I)),
]

_LEVEL_WORDS = r"(low|very\s+low|moderate|medium|high|very\s+high)"
_LEVEL_FIELDS = {
    "climate.rainfall": re.compile(rf"rainfall(?:\s+is|\s*[:=])?\s*{_LEVEL_WORDS}", re.I),
    "climate.temperature": re.compile(rf"temperature(?:\s+is|\s*[:=])?\s*{_LEVEL_WORDS}", re.I),
    "biodiversity.species_richness": re.compile(rf"species\s+richness(?:\s+is|\s*[:=])?\s*{_LEVEL_WORDS}", re.I),
    "biodiversity.habitat_diversity": re.compile(rf"habitat\s+diversity(?:\s+is|\s*[:=])?\s*{_LEVEL_WORDS}", re.I),
    "human_impact.pollution": re.compile(rf"pollution(?:\s+is|\s*[:=])?\s*{_LEVEL_WORDS}", re.I),
    "human_impact.deforestation": re.compile(rf"deforestation(?:\s+is|\s*[:=])?\s*{_LEVEL_WORDS}", re.I),
    "human_impact.fragmentation": re.compile(rf"fragmentation(?:\s+is|\s*[:=])?\s*{_LEVEL_WORDS}", re.I),
    "human_impact.urbanization": re.compile(rf"urban(?:ization)?(?:\s+is|\s*[:=])?\s*{_LEVEL_WORDS}", re.I),
}

_LAND_USE_RE = re.compile(
    r"\b(monoculture|polyculture|crop\s+rotation|agroforestry|pasture|grassland|forest|wetland|urban|orchard)\b",
    re.I,
)
_CROP_RE = re.compile(r"\bgrow(?:ing)?\s+([a-zA-Z\- ]{3,20}?)(?:\.|,| in| on| continuously|$)", re.I)
_REGION_RE = re.compile(
    r"\b(semi-arid|arid|tropical|temperate|mediterranean|subtropical|savanna|alpine|coastal)\b", re.I
)
_MONOCULTURE_CROP_RE = re.compile(r"monoculture\s+([a-zA-Z]+)", re.I)


def extract_from_text(text: str) -> Dict[str, Any]:
    """Best-effort deterministic extraction of environmental variables from free text."""
    updates: Dict[str, Any] = {}

    for field, pattern in _PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        value = float(m.group(1))
        if field == "climate.rainfall_num":
            updates["climate.rainfall"] = f"{value} mm/year"
        else:
            updates[field] = value

    for field, pattern in _LEVEL_FIELDS.items():
        if field in updates:
            continue
        m = pattern.search(text)
        if m:
            updates[field] = re.sub(r"\s+", " ", m.group(1).lower().strip())

    land_use_match = _LAND_USE_RE.search(text)
    if land_use_match:
        updates["land_use"] = land_use_match.group(1).lower()

    mono_crop = _MONOCULTURE_CROP_RE.search(text)
    if mono_crop:
        updates.setdefault("land_use", "monoculture")
        updates["crop"] = mono_crop.group(1).lower()
    else:
        crop_match = _CROP_RE.search(text)
        if crop_match:
            updates["crop"] = crop_match.group(1).strip().lower()

    region_match = _REGION_RE.search(text)
    if region_match:
        updates["location.region"] = region_match.group(1).lower()

    return updates


def _set_nested(state: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    node = state
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value


def _get_nested(state: Dict[str, Any], dotted_key: str) -> Any:
    parts = dotted_key.split(".")
    node: Any = state
    for p in parts:
        if not isinstance(node, dict) or p not in node:
            return None
        node = node[p]
    return node


def merge_updates(base_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merges dotted-key updates (from NL extraction) into the nested state dict."""
    state = _deep_copy(base_state)
    for key, value in updates.items():
        if value is None:
            continue
        _set_nested(state, key, value)
    return state


def merge_structured_input(base_state: Dict[str, Any], structured: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges an incoming structured JSON payload (which may itself be
    nested, e.g. {"soil": {"ph": 7.5}}) into the environmental state.
    """
    state = _deep_copy(base_state)
    _deep_merge(state, structured)
    return state


def _deep_copy(d: Dict[str, Any]) -> Dict[str, Any]:
    import copy

    return copy.deepcopy(d) if d else {}


def _deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    for k, v in source.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            _deep_merge(target[k], v)
        elif v is not None:
            target[k] = v


def detect_missing_fields(state: Dict[str, Any], prioritize_core: bool = True) -> List[str]:
    """Returns a list of human-readable questions for missing core fields."""
    missing = []
    fields = CORE_FIELDS if prioritize_core else ALL_TRACKED_FIELDS
    for field in fields:
        if _get_nested(state, field) in (None, ""):
            missing.append(FIELD_QUESTIONS.get(field, field))
    return missing


def state_completeness(state: Dict[str, Any]) -> float:
    """Fraction of ALL_TRACKED_FIELDS that are populated. Used in confidence scoring."""
    filled = sum(1 for f in ALL_TRACKED_FIELDS if _get_nested(state, f) not in (None, ""))
    return round(filled / len(ALL_TRACKED_FIELDS), 3)


def empty_state() -> Dict[str, Any]:
    return EnvironmentalState().model_dump()
