"""
Deterministic reasoning engine (spec section 15).

This is the core differentiator: recommendations are never produced by
just asking an LLM to "reason". Instead:

1. The user's environmental state is evaluated against a rule set that
   identifies which condition thresholds are triggered (e.g. "soil
   organic carbon is low").
2. Triggered conditions are traced through the environmental
   relationship graph (app/models/knowledge.py: EnvironmentalRelationship)
   to find which downstream metrics are affected and how.
3. Only when >=3 distinct metrics are connected in one causal chain does
   the engine propose intervention *categories* (not final prose —
   that's the recommendation engine's job, using retrieved evidence).

The LLM is used later, only to phrase the already-derived reasoning and
to synthesize retrieved evidence into readable prose — never to invent
the causal relationships themselves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.models.knowledge import EnvironmentalRelationship

# --- Condition thresholds ----------------------------------------------


@dataclass
class TriggeredCondition:
    metric: str
    state: str  # "low" | "high" | "monoculture" | etc.
    detail: str


def _is_low(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("low", "very low")
    if isinstance(value, (int, float)):
        return value < 30  # generic percentile-style fallback
    return False


def _is_high(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("high", "very high")
    if isinstance(value, (int, float)):
        return value > 70
    return False


def evaluate_conditions(state: Dict[str, Any]) -> List[TriggeredCondition]:
    triggered: List[TriggeredCondition] = []

    soil = state.get("soil", {}) or {}
    oc = soil.get("organic_carbon")
    if isinstance(oc, (int, float)) and oc < 1.0:
        triggered.append(
            TriggeredCondition("soil_organic_carbon", "low", f"Soil organic carbon is {oc}%, below the ~1% threshold typically associated with degraded soils.")
        )
    if isinstance(oc, (int, float)) and oc >= 2.0:
        triggered.append(
            TriggeredCondition("soil_organic_carbon", "high", f"Soil organic carbon is {oc}%, indicating relatively healthy soil structure.")
        )

    rainfall = (state.get("climate", {}) or {}).get("rainfall")
    if _is_low(rainfall):
        triggered.append(TriggeredCondition("rainfall", "low", f"Rainfall reported as low ({rainfall})."))
    if _is_high(rainfall):
        triggered.append(TriggeredCondition("rainfall", "high", f"Rainfall reported as high ({rainfall})."))

    land_use = (state.get("land_use") or "").lower()
    if "monoculture" in land_use:
        triggered.append(TriggeredCondition("land_use", "monoculture", "Land use is monoculture, which structurally reduces habitat and vegetation diversity."))

    human_impact = state.get("human_impact", {}) or {}
    for key in ("deforestation", "fragmentation", "pollution", "urbanization", "agricultural_pressure"):
        v = human_impact.get(key)
        if _is_high(v):
            triggered.append(TriggeredCondition(f"human_impact.{key}", "high", f"{key.replace('_', ' ').title()} reported as high."))

    biodiversity = state.get("biodiversity", {}) or {}
    for key in ("species_richness", "habitat_diversity", "pollinator_diversity", "vegetation_diversity"):
        v = biodiversity.get(key)
        if _is_low(v):
            triggered.append(TriggeredCondition(f"biodiversity.{key}", "low", f"{key.replace('_', ' ').title()} reported as low."))

    temperature = (state.get("climate", {}) or {}).get("temperature")
    if _is_high(temperature):
        triggered.append(TriggeredCondition("temperature", "high", f"Temperature reported as high ({temperature})."))

    return triggered


# --- Graph traversal -----------------------------------------------------

# Canonical metric name aliases so triggered-condition names line up with
# the relationship graph's source_metric / target_metric vocabulary.
_METRIC_ALIASES = {
    "soil_organic_carbon": "soil carbon",
    "rainfall": "rainfall",
    "land_use": "monoculture",
    "temperature": "temperature",
    "human_impact.deforestation": "deforestation",
    "human_impact.fragmentation": "land fragmentation",
    "human_impact.pollution": "pesticide pressure",
    "human_impact.urbanization": "urbanization",
    "human_impact.agricultural_pressure": "monoculture",
    "biodiversity.species_richness": "species richness",
    "biodiversity.habitat_diversity": "habitat diversity",
    "biodiversity.pollinator_diversity": "pollinator diversity",
    "biodiversity.vegetation_diversity": "plant diversity",
}


@dataclass
class ReasoningChain:
    triggered_metrics: List[str]
    edges: List[Dict[str, str]]  # source_metric, relationship, target_metric, direction, strength
    downstream_metrics: Set[str]

    def is_multi_metric(self, min_metrics: int = 3) -> bool:
        connected_metrics = set(self.triggered_metrics) | set(self.downstream_metrics)

        # Count distinct environmental metrics represented in the reasoning chain.
        for edge in self.edges:
            connected_metrics.add(edge["source_metric"])
            connected_metrics.add(edge["target_metric"])

        return len(connected_metrics) >= min_metrics


def build_reasoning_chain(
    db: Session, triggered: List[TriggeredCondition], max_hops: int = 3
) -> ReasoningChain:
    """
    Breadth-first traversal of the relationship graph starting from every
    triggered condition's canonical metric name, up to `max_hops` deep.
    """
    all_edges: List[EnvironmentalRelationship] = db.query(EnvironmentalRelationship).all()
    edge_index: Dict[str, List[EnvironmentalRelationship]] = {}
    for e in all_edges:
        edge_index.setdefault(e.source_metric.lower(), []).append(e)

    frontier = {
        _METRIC_ALIASES.get(t.metric, t.metric.replace("_", " ")) for t in triggered
    }
    triggered_names = set(frontier)
    visited: Set[str] = set(frontier)
    result_edges: List[Dict[str, str]] = []
    downstream: Set[str] = set()

    for _ in range(max_hops):
        next_frontier: Set[str] = set()
        for metric in frontier:
            for e in edge_index.get(metric.lower(), []):
                result_edges.append(
                    {
                        "source_metric": e.source_metric,
                        "relationship": e.relationship,
                        "target_metric": e.target_metric,
                        "direction": e.direction,
                        "strength": e.strength,
                    }
                )
                if e.target_metric not in visited:
                    next_frontier.add(e.target_metric)
                    downstream.add(e.target_metric)
                    visited.add(e.target_metric)
        if not next_frontier:
            break
        frontier = next_frontier

    return ReasoningChain(
        triggered_metrics=sorted(triggered_names),
        edges=result_edges,
        downstream_metrics=downstream,
    )


# --- Intervention category mapping --------------------------------------

_INTERVENTION_RULES = [
    # (required triggered-condition metrics subset, intervention categories)
    ({"soil_organic_carbon:low"}, ["cover crops", "crop rotation", "organic residue retention"]),
    ({"land_use:monoculture"}, ["intercropping", "crop rotation", "agroforestry", "native vegetation strips"]),
    ({"rainfall:low"}, ["water retention practices", "agroforestry", "drought-tolerant cover crops"]),
    ({"human_impact.fragmentation:high"}, ["native vegetation corridors", "habitat connectivity restoration"]),
    ({"human_impact.deforestation:high"}, ["agroforestry", "native vegetation corridors", "reforestation buffers"]),
    ({"human_impact.pollution:high"}, ["reduced pesticide/agrochemical input", "integrated pest management"]),
    ({"biodiversity.pollinator_diversity:low"}, ["native flowering strips", "reduced pesticide pressure", "intercropping"]),
]


def suggest_intervention_categories(triggered: List[TriggeredCondition]) -> List[str]:
    triggered_keys = {f"{t.metric}:{t.state}" for t in triggered}
    categories: List[str] = []
    for required, cats in _INTERVENTION_RULES:
        if required & triggered_keys:
            for c in cats:
                if c not in categories:
                    categories.append(c)
    return categories


def run_reasoning(db: Session, state: Dict[str, Any]) -> Dict[str, Any]:
    triggered = evaluate_conditions(state)
    chain = build_reasoning_chain(db, triggered)
    interventions = suggest_intervention_categories(triggered)

    drivers = [t.detail for t in triggered]

    return {
        "triggered_conditions": triggered,
        "reasoning_chain": chain,
        "intervention_categories": interventions,
        "drivers": drivers,
        "is_multi_metric": chain.is_multi_metric(min_metrics=3),
    }
