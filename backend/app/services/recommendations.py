"""
Recommendation engine (spec section 5).

For each intervention category surfaced by the deterministic reasoning
engine, this module:
1. Retrieves evidence specific to that intervention (a separate, more
   targeted retrieval call than the general context retrieval).
2. Synthesizes a recommendation from that evidence (LLM-assisted when
   available, deterministic template otherwise -- see llm.py).
3. Computes affected metrics / expected effect from the reasoning chain.
4. Computes evidence-based confidence (never invented).
5. Runs evidence verification before the recommendation is returned.
"""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.prompts.recommendation_prompt import RECOMMENDATION_PROMPT
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services import llm
from app.services.evidence import verify_recommendation
from app.services.reasoning import ReasoningChain, TriggeredCondition
from app.services.retrieval import RetrievedChunk, retrieve

# Deterministic fallback phrasing per intervention category. Used when no
# LLM is configured (DEMO_MODE) or when the LLM call fails/returns
# unusable output -- the system must remain demonstrable in both cases.
_TEMPLATES: Dict[str, str] = {
    "cover crops": (
        "Introduce a legume-based cover crop (e.g. clover or vetch) between main "
        "cropping cycles, retaining residues rather than tilling them under. This adds "
        "organic inputs to the soil and can support soil structure and moisture retention."
    ),
    "crop rotation": (
        "Replace continuous single-crop cycles with a rotation that includes a "
        "nitrogen-fixing legume and a deep-rooted species, breaking pest/disease cycles "
        "tied to monoculture and diversifying root structure in the soil profile."
    ),
    "organic residue retention": (
        "Retain crop residues on the field after harvest instead of removing or burning "
        "them, returning organic matter to the topsoil layer."
    ),
    "intercropping": (
        "Interplant the primary crop with a companion species (e.g. a legume or "
        "flowering companion plant) in alternating rows, increasing structural and "
        "flowering diversity within the same field."
    ),
    "agroforestry": (
        "Integrate scattered or boundary trees/shrubs (native, regionally adapted "
        "species) into the cropped area, adding a woody vegetation layer that "
        "monoculture cropland otherwise lacks."
    ),
    "native vegetation strips": (
        "Establish strips of native vegetation along field margins or between plots to "
        "provide non-crop habitat within an otherwise uniform planting."
    ),
    "water retention practices": (
        "Adopt water retention practices such as contour bunding, mulching, or small "
        "basin/swale earthworks to capture and hold rainfall on-site rather than losing "
        "it to runoff."
    ),
    "drought-tolerant cover crops": (
        "Use a drought-tolerant, low-water cover crop mix suited to the regional rainfall "
        "regime rather than leaving soil bare between cropping cycles."
    ),
    "native vegetation corridors": (
        "Establish or restore corridors of native vegetation connecting fragmented "
        "habitat patches, re-linking areas that have become isolated."
    ),
    "habitat connectivity restoration": (
        "Prioritize restoring physical connectivity between remaining habitat patches "
        "(e.g. hedgerows, riparian buffers) rather than treating patches in isolation."
    ),
    "reforestation buffers": (
        "Establish native-species reforestation buffers along the edges of cleared or "
        "degraded land adjacent to remaining forest."
    ),
    "reduced pesticide/agrochemical input": (
        "Reduce broad-spectrum pesticide/agrochemical application, shifting toward "
        "targeted application timed to pest pressure rather than routine scheduling."
    ),
    "integrated pest management": (
        "Adopt integrated pest management (monitoring-based intervention, biological "
        "controls, and targeted application) in place of routine broad-spectrum spraying."
    ),
    "native flowering strips": (
        "Plant native flowering strips or hedgerows along field margins to provide "
        "forage resources for pollinators across the growing season."
    ),
}

_DEFAULT_TIME_HORIZON = {
    "cover crops": {"short_term": "0-1 season: soil cover established", "medium_term": "1-3 years: measurable soil organic matter change", "long_term": "3+ years: improved soil structure and biological activity"},
    "crop rotation": {"short_term": "1 cycle: pest/disease pressure shift", "medium_term": "2-3 years: root diversity effects on soil structure", "long_term": "3+ years: cumulative soil health change"},
    "agroforestry": {"short_term": "1-2 years: tree establishment", "medium_term": "3-5 years: canopy and root structure develop", "long_term": "5-10+ years: full structural and microclimate benefits"},
}
_GENERIC_TIME_HORIZON = {
    "short_term": "0-1 year: practice establishment, minimal measurable change yet",
    "medium_term": "1-3 years: early structural/biological change",
    "long_term": "3+ years: cumulative ecosystem-level effects",
}

_EXPECTED_EFFECTS: Dict[str, Dict[str, str]] = {
    "cover crops": {"soil_organic_carbon": "increase", "soil_moisture": "increase", "biodiversity": "increase"},
    "crop rotation": {"soil_organic_carbon": "increase", "habitat_diversity": "increase"},
    "intercropping": {"habitat_diversity": "increase", "pollinator_diversity": "increase"},
    "agroforestry": {"habitat_diversity": "increase", "soil_moisture": "increase", "species_richness": "increase"},
    "native vegetation strips": {"habitat_diversity": "increase", "pollinator_diversity": "increase"},
    "water retention practices": {"soil_moisture": "increase"},
    "drought-tolerant cover crops": {"soil_moisture": "increase", "soil_organic_carbon": "increase"},
    "native vegetation corridors": {"fragmentation": "decrease", "species_richness": "increase"},
    "habitat connectivity restoration": {"fragmentation": "decrease"},
    "reforestation buffers": {"deforestation": "decrease", "habitat_diversity": "increase"},
    "reduced pesticide/agrochemical input": {"pollinator_diversity": "increase", "pollution": "decrease"},
    "integrated pest management": {"pollinator_diversity": "increase"},
    "native flowering strips": {"pollinator_diversity": "increase"},
}


def _confidence(
    chunks: List[RetrievedChunk], completeness: float, agreement_bonus: float
) -> tuple[float, str]:
    if not chunks:
        return 0.0, "Low"
    avg_relevance = sum(c.relevance for c in chunks) / len(chunks)
    source_count_factor = min(1.0, len(chunks) / 3)
    credibility_factor = sum(
        1.0 if c.credibility_tier in ("authoritative", "peer_reviewed") else 0.6
        for c in chunks
    ) / len(chunks)
    score = (
        0.4 * avg_relevance
        + 0.2 * source_count_factor
        + 0.2 * credibility_factor
        + 0.1 * completeness
        + 0.1 * agreement_bonus
    )
    score = round(min(1.0, score), 2)
    if score >= 0.7:
        label = "High"
    elif score >= 0.45:
        label = "Medium"
    else:
        label = "Low"
    return score, label


def _affected_metrics_for(category: str, chain: ReasoningChain) -> List[str]:
    base = list(_EXPECTED_EFFECTS.get(category, {}).keys())
    for m in chain.downstream_metrics:
        if m not in base:
            base.append(m)
    return base[:5]


def generate_recommendations(
    db: Session,
    state: Dict[str, Any],
    intervention_categories: List[str],
    chain: ReasoningChain,
    completeness: float,
    max_recommendations: int = 4,
) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []

    for category in intervention_categories[:max_recommendations]:
        query = f"{category} biodiversity soil {state.get('land_use', '')} {state.get('location', {}).get('region', '')}"
        evidence_chunks = retrieve(db, query, top_k=3)

        rec_text = None
        if evidence_chunks:
            evidence_str = "\n".join(f"- ({c.organization or 'unknown source'}) {c.text}" for c in evidence_chunks)
            prompt = RECOMMENDATION_PROMPT.format(
                intervention_category=category, state=state, evidence=evidence_str
            )
            rec_text = llm.generate(SYSTEM_PROMPT, prompt)

        if not rec_text:
            rec_text = _TEMPLATES.get(
                category,
                f"Implement {category}, a targeted intervention for the drivers identified in this assessment.",
            )

        affected_metrics = _affected_metrics_for(category, chain)
        expected_effect = _EXPECTED_EFFECTS.get(category, {})
        time_horizon = _DEFAULT_TIME_HORIZON.get(category, _GENERIC_TIME_HORIZON)

        agreement_bonus = 1.0 if len({c.document_id for c in evidence_chunks}) > 1 else 0.5
        confidence, confidence_label = _confidence(evidence_chunks, completeness, agreement_bonus)

        scientific_reasoning = _build_scientific_reasoning(category, chain, evidence_chunks)

        if not evidence_chunks:
            recommendations.append(
                {
                    "recommendation": "Evidence insufficient for a confident recommendation. Additional environmental information is required.",
                    "scientific_reasoning": "No retrieved evidence met the similarity threshold for this intervention category.",
                    "affected_metrics": [],
                    "time_horizon": {},
                    "expected_effect": {},
                    "confidence": 0.0,
                    "confidence_label": "Low",
                    "evidence": [],
                    "intervention_category": category,
                }
            )
            continue

        rec_dict = {
            "recommendation": rec_text.strip(),
            "scientific_reasoning": scientific_reasoning,
            "affected_metrics": affected_metrics,
            "time_horizon": time_horizon,
            "expected_effect": expected_effect,
            "confidence": confidence,
            "confidence_label": confidence_label,
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
                for c in evidence_chunks
            ],
            "intervention_category": category,
        }

        verification = verify_recommendation(rec_dict, evidence_chunks)
        if not verification["supported"]:
            rec_dict["recommendation"] = (
                "Evidence insufficient for a confident recommendation. Additional environmental "
                "information is required. (" + "; ".join(verification["issues"]) + ")"
            )
            rec_dict["confidence"] = 0.0
            rec_dict["confidence_label"] = "Low"

        recommendations.append(rec_dict)

    return recommendations


def _build_scientific_reasoning(category: str, chain: ReasoningChain, chunks: List[RetrievedChunk]) -> str:
    edge_desc = "; ".join(
        f"{e['source_metric']} {e['relationship']} {e['target_metric']}" for e in chain.edges[:4]
    )
    source_desc = ", ".join(sorted({c.organization or "curated knowledge base" for c in chunks}))
    reasoning = (
        f"This intervention ({category}) is connected to the observed conditions through the "
        f"following relationship chain: {edge_desc or 'multiple interacting environmental metrics'}. "
        f"Supporting evidence was retrieved from: {source_desc}."
    )
    return reasoning
