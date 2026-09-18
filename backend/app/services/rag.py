"""
RAG pipeline orchestration (spec section 6):

User Query -> Query Understanding -> Environmental State Extraction ->
Missing Information Detection -> Query Expansion -> Embedding Generation ->
Vector Search -> Metadata Filtering -> Evidence Ranking -> Multi-Metric
Reasoning -> Recommendation Generation -> Evidence Verification ->
Structured Response

This module is the single entry point the /api/chat and /api/analyze
endpoints call into.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.prompts.final_response_prompt import FINAL_RESPONSE_PROMPT
from app.prompts.reasoning_prompt import REASONING_PROMPT
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services import llm
from app.services.conversation import (
    detect_missing_fields,
    extract_from_text,
    merge_structured_input,
    merge_updates,
    state_completeness,
)
from app.services.reasoning import run_reasoning
from app.services.recommendations import generate_recommendations
from app.services.retrieval import compress_context, retrieve


def process_turn(
    db: Session,
    *,
    message: str,
    current_state: Dict[str, Any],
    structured_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Runs one full RAG + reasoning + recommendation turn and returns a
    dict matching the ChatResponse schema (minus conversation_id, which
    the caller/endpoint fills in).
    """
    # 1. Query understanding + 2. environmental state extraction
    nl_updates = extract_from_text(message)
    state = merge_updates(current_state, nl_updates)
    if structured_input:
        state = merge_structured_input(state, structured_input)

    # 3. Missing information detection
    missing_fields = detect_missing_fields(state)
    completeness = state_completeness(state)

    # If core information is missing, ask for it before doing anything else.
    # (We still run a light retrieval below so the response isn't a dead end,
    # but we do not fabricate recommendations from an incomplete state.)
    needs_more_info = len(missing_fields) >= 3  # tolerate 1-2 gaps, insist on the rest

    # 4. Query expansion (deterministic; LLM-assisted rewrite when available)
    expanded_query = _expand_query(state, message)

    # 5-8. Embedding generation, vector search, metadata filtering, evidence ranking
    region = (state.get("location") or {}).get("region")
    general_evidence = retrieve(db, expanded_query, region=region)
    general_evidence = compress_context(general_evidence)

    # 9. Multi-metric reasoning
    reasoning_result = run_reasoning(db, state)
    chain = reasoning_result["reasoning_chain"]
    triggered = reasoning_result["triggered_conditions"]
    drivers = reasoning_result["drivers"]
    intervention_categories = reasoning_result["intervention_categories"]

    recommendations: List[Dict[str, Any]] = []
    if not needs_more_info and intervention_categories:
        # 10. Recommendation generation + 11. evidence verification (inside)
        recommendations = generate_recommendations(
            db, state, intervention_categories, chain, completeness
        )

    assessment = _build_assessment(state, triggered)

    overall_confidence = (
        round(sum(r["confidence"] for r in recommendations) / len(recommendations), 2)
        if recommendations
        else 0.0
    )

    response_text = _build_response_text(
        needs_more_info, missing_fields, assessment, drivers, recommendations, message
    )

    return {
        "response": response_text,
        "needs_more_information": needs_more_info,
        "missing_fields": missing_fields if needs_more_info else [],
        "environmental_assessment": assessment,
        "drivers": drivers,
        "relationships": chain.edges,
        "recommendations": recommendations,
        "evidence": [
            {
                "chunk_id": c.chunk_id,
                "title": c.title,
                "organization": c.organization,
                "source_url": c.source_url,
                "publication_year": c.publication_year,
                "document_type": c.document_type,
                "relevance": c.relevance,
                "text_snippet": c.text[:220],
            }
            for c in general_evidence
        ],
        "confidence": overall_confidence,
        "updated_state": state,
        "demo_mode": llm.is_demo_mode(),
    }


def _expand_query(state: Dict[str, Any], message: str) -> str:
    soil = state.get("soil", {}) or {}
    climate = state.get("climate", {}) or {}
    human_impact = state.get("human_impact", {}) or {}
    biodiversity = state.get("biodiversity", {}) or {}
    parts = [
        message,
        f"land use {state.get('land_use') or ''}",
        f"crop {state.get('crop') or ''}",
        f"region {(state.get('location') or {}).get('region') or ''}",
        f"soil organic carbon {soil.get('organic_carbon') or ''}",
        f"rainfall {climate.get('rainfall') or ''}",
        f"deforestation {human_impact.get('deforestation') or ''}",
        f"fragmentation {human_impact.get('fragmentation') or ''}",
        f"species richness {biodiversity.get('species_richness') or ''}",
    ]
    return " ".join(p for p in parts if p.strip())


def _build_assessment(state: Dict[str, Any], triggered) -> Dict[str, Any]:
    """
    Build environmental assessment with metric-specific semantics.

    Important:
    - Low soil condition -> Low soil health
    - Low rainfall -> Low water availability
    - Low rainfall / high temperature -> High climate stress
    - Low biodiversity indicators -> Low biodiversity
    - High human-impact indicators -> High human impact
    """

    soil_states = [
        t.state for t in triggered
        if t.metric.startswith("soil")
    ]

    rainfall_states = [
        t.state for t in triggered
        if t.metric == "rainfall"
    ]

    biodiversity_states = [
        t.state for t in triggered
        if t.metric.startswith("biodiversity")
    ]

    temperature_states = [
        t.state for t in triggered
        if t.metric == "temperature"
    ]

    human_states = [
        t.state for t in triggered
        if t.metric.startswith("human_impact")
    ]

    # Soil health: low condition means low health.
    if "low" in soil_states:
        soil_health = "Low"
    elif "high" in soil_states:
        soil_health = "High"
    elif soil_states:
        soil_health = "Moderate"
    else:
        soil_health = "Unknown"

    # Water availability: low rainfall means low water availability.
    if "low" in rainfall_states:
        water_availability = "Low"
    elif "high" in rainfall_states:
        water_availability = "High"
    elif rainfall_states:
        water_availability = "Moderate"
    else:
        water_availability = "Unknown"

    # Climate stress has inverse semantics:
    # low rainfall or high temperature increases climate stress.
    if "low" in rainfall_states or "high" in temperature_states:
        climate_stress = "High"
    elif "high" in rainfall_states:
        climate_stress = "Low"
    elif rainfall_states or temperature_states:
        climate_stress = "Moderate"
    else:
        climate_stress = "Unknown"

    # Biodiversity assessment should only use actual biodiversity indicators.
    if "low" in biodiversity_states:
        biodiversity = "Low"
    elif "high" in biodiversity_states:
        biodiversity = "High"
    elif biodiversity_states:
        biodiversity = "Moderate"
    else:
        biodiversity = "Unknown"

    # Human impact: high reported pressure means high human impact.
    if "high" in human_states:
        human_impact = "High"
    elif "low" in human_states:
        human_impact = "Low"
    elif human_states:
        human_impact = "Moderate"
    else:
        human_impact = "Unknown"

    return {
        "soil_health": soil_health,
        "water_availability": water_availability,
        "biodiversity": biodiversity,
        "climate_stress": climate_stress,
        "human_impact": human_impact,
        "raw_state": state,
    }

def _build_response_text(
    needs_more_info: bool,
    missing_fields: List[str],
    assessment: Dict[str, Any],
    drivers: List[str],
    recommendations: List[Dict[str, Any]],
    message: str,
) -> str:
    if needs_more_info:
        questions = "\n".join(f"{i+1}. {f}" for i, f in enumerate(missing_fields))
        return (
            "To assess the likely causes, I need a few more details:\n"
            f"{questions}"
        )

    structured_summary = {
        "assessment": {k: v for k, v in assessment.items() if k != "raw_state"},
        "drivers": drivers,
        "top_recommendation": recommendations[0]["recommendation"] if recommendations else None,
    }

    llm_text = llm.generate(
        SYSTEM_PROMPT, FINAL_RESPONSE_PROMPT.format(structured_data=structured_summary)
    )
    if llm_text:
        return llm_text.strip()

    # Deterministic fallback (demo mode / LLM unavailable)
    if not drivers:
        return (
            "Based on the information provided, no strongly degraded conditions were "
            "detected against the current rule set. Share more detail (soil, climate, "
            "human impact indicators) for a deeper assessment."
        )
    lines = ["Environmental assessment based on the information provided:"]
    for k, v in assessment.items():
        if k == "raw_state":
            continue
        lines.append(f"- {k.replace('_', ' ').title()}: {v}")
    lines.append("\nKey drivers identified:")
    for d in drivers:
        lines.append(f"- {d}")
    if recommendations:
        lines.append(f"\nTop recommendation: {recommendations[0]['recommendation']}")
    return "\n".join(lines)
