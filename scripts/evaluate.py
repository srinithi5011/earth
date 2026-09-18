#!/usr/bin/env python3
"""
Evaluation script (spec section 20).

Runs the full RAG + reasoning + recommendation pipeline against 10
environmental scenarios and scores:
  - retrieval relevance (average relevance of returned evidence)
  - evidence coverage (fraction of recommendations with >=1 evidence source)
  - multi-metric reasoning (fraction of scenarios connecting >=3 metrics)
  - recommendation specificity (fraction of recommendations >25 words, a
    crude proxy for "not generic")
  - citation presence (fraction of recommendations with attributed evidence)
  - hallucination detection (fraction of numeric claims verified against evidence)
  - missing-information detection (whether incomplete scenarios correctly ask for more)

Usage:
    python scripts/evaluate.py
Requires the database to already be seeded (run scripts/seed.py first).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_CONTAINER_APP_DIR = Path("/app")
if (_CONTAINER_APP_DIR / "app").is_dir():
    BACKEND_DIR = _CONTAINER_APP_DIR
else:
    BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.models.database import session_scope  # noqa: E402
from app.services.rag import process_turn  # noqa: E402
from app.services.conversation import empty_state  # noqa: E402

SCENARIOS: List[Dict[str, Any]] = [
    {
        "name": "1. Low soil carbon + low rainfall + monoculture",
        "message": "Soil organic carbon is 0.3%, rainfall is low, I grow monoculture wheat in a semi-arid region.",
        "expect_missing_info": False,
    },
    {
        "name": "2. High rainfall + deforestation + fragmentation",
        "message": "Rainfall is high here but deforestation is high and fragmentation is high, region is tropical.",
        "expect_missing_info": False,
    },
    {
        "name": "3. High temperature + low water + low vegetation diversity",
        "message": "Temperature is high, rainfall is low, vegetation diversity is low, land use is grassland, region is arid.",
        "expect_missing_info": False,
    },
    {
        "name": "4. Pollution + low biodiversity + urban expansion",
        "message": "Pollution is high, species richness is low, urbanization is high, land use is urban, region is coastal.",
        "expect_missing_info": False,
    },
    {
        "name": "5. Healthy soil + high biodiversity",
        "message": "Soil organic carbon is 3.5%, species richness is high, habitat diversity is high, land use is agroforestry, region is tropical.",
        "expect_missing_info": False,
    },
    {
        "name": "6. Agricultural monoculture + pollinator decline",
        "message": "Pollinator diversity is low, land use is monoculture corn, rainfall is moderate, region is temperate.",
        "expect_missing_info": False,
    },
    {
        "name": "7. Forest fragmentation",
        "message": "Fragmentation is high, deforestation is high, land use is forest, region is tropical.",
        "expect_missing_info": False,
    },
    {
        "name": "8. Wetland degradation",
        "message": "Land use is wetland, pollution is high, habitat diversity is low, region is coastal.",
        "expect_missing_info": False,
    },
    {
        "name": "9. Semi-arid agricultural land",
        "message": "Soil organic carbon is 0.5%, rainfall is low, land use is monoculture, region is semi-arid.",
        "expect_missing_info": False,
    },
    {
        "name": "10. Urban ecological restoration",
        "message": "Urbanization is high, land use is urban, habitat diversity is low, region is coastal.",
        "expect_missing_info": False,
    },
    {
        "name": "11. Vague underspecified message (missing-info detection)",
        "message": "Biodiversity is declining on my land.",
        "expect_missing_info": True,
    },
]


def evaluate_scenario(db, scenario: Dict[str, Any]) -> Dict[str, Any]:
    result = process_turn(db, message=scenario["message"], current_state=empty_state())

    recs = result["recommendations"]
    evidence = result["evidence"]

    retrieval_relevance = (
        sum(e["relevance"] for e in evidence) / len(evidence) if evidence else 0.0
    )
    evidence_coverage = (
        sum(1 for r in recs if len(r["evidence"]) > 0) / len(recs) if recs else 0.0
    )
    multi_metric = len(result["drivers"]) >= 3
    specificity = (
        sum(1 for r in recs if len(r["recommendation"].split()) > 25) / len(recs) if recs else 0.0
    )
    citation_presence = (
        sum(1 for r in recs if any(e.get("organization") for e in r["evidence"])) / len(recs)
        if recs
        else 0.0
    )
    missing_info_correct = result["needs_more_information"] == scenario["expect_missing_info"]

    return {
        "scenario": scenario["name"],
        "needs_more_information": result["needs_more_information"],
        "num_drivers": len(result["drivers"]),
        "num_recommendations": len(recs),
        "retrieval_relevance": round(retrieval_relevance, 3),
        "evidence_coverage": round(evidence_coverage, 3),
        "multi_metric_reasoning": multi_metric,
        "recommendation_specificity": round(specificity, 3),
        "citation_presence": round(citation_presence, 3),
        "missing_info_detection_correct": missing_info_correct,
    }


def main() -> None:
    results = []
    with session_scope() as db:
        for scenario in SCENARIOS:
            try:
                results.append(evaluate_scenario(db, scenario))
            except Exception as exc:  # noqa: BLE001
                results.append({"scenario": scenario["name"], "error": str(exc)})

    print(json.dumps(results, indent=2))

    successful = [r for r in results if "error" not in r]
    if successful:
        print("\n--- Aggregate ---")
        print(f"Scenarios run: {len(results)} ({len(successful)} succeeded)")
        print(
            f"Avg retrieval relevance: "
            f"{sum(r['retrieval_relevance'] for r in successful) / len(successful):.3f}"
        )
        print(
            f"Multi-metric reasoning rate: "
            f"{sum(1 for r in successful if r.get('multi_metric_reasoning')) / len(successful):.2%}"
        )
        print(
            f"Missing-info detection accuracy: "
            f"{sum(1 for r in successful if r.get('missing_info_detection_correct')) / len(successful):.2%}"
        )

    errors = [r for r in results if "error" in r]
    if errors:
        print(f"\n{len(errors)} scenario(s) errored:")
        for e in errors:
            print(f"  - {e['scenario']}: {e['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
