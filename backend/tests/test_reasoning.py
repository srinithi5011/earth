from app.models.knowledge import EnvironmentalRelationship
from app.services.reasoning import evaluate_conditions, run_reasoning, suggest_intervention_categories


def _seed_minimal_relationships(db):
    rows = [
        EnvironmentalRelationship(
            source_metric="soil carbon", relationship="increases", target_metric="water retention",
            direction="positive", strength="strong", scientific_basis="test",
        ),
        EnvironmentalRelationship(
            source_metric="water retention", relationship="increases", target_metric="plant resilience",
            direction="positive", strength="moderate", scientific_basis="test",
        ),
        EnvironmentalRelationship(
            source_metric="monoculture", relationship="reduces", target_metric="habitat diversity",
            direction="negative", strength="strong", scientific_basis="test",
        ),
        EnvironmentalRelationship(
            source_metric="habitat diversity", relationship="increases", target_metric="species richness",
            direction="positive", strength="strong", scientific_basis="test",
        ),
    ]
    for r in rows:
        db.add(r)
    db.commit()


def test_evaluate_conditions_detects_low_organic_carbon():
    state = {"soil": {"organic_carbon": 0.3}, "climate": {"rainfall": "low"}, "land_use": "monoculture wheat"}
    triggered = evaluate_conditions(state)
    metrics = {t.metric for t in triggered}
    assert "soil_organic_carbon" in metrics
    assert "rainfall" in metrics
    assert "land_use" in metrics


def test_evaluate_conditions_no_false_positive_on_healthy_state():
    state = {"soil": {"organic_carbon": 3.5}, "climate": {"rainfall": "high"}, "land_use": "agroforestry"}
    triggered = evaluate_conditions(state)
    metrics = {t.metric for t in triggered}
    assert "land_use" not in metrics  # only monoculture triggers land_use


def test_suggest_intervention_categories_for_low_carbon_monoculture():
    state = {"soil": {"organic_carbon": 0.3}, "climate": {"rainfall": "low"}, "land_use": "monoculture wheat"}
    triggered = evaluate_conditions(state)
    categories = suggest_intervention_categories(triggered)
    assert "cover crops" in categories
    assert "intercropping" in categories or "crop rotation" in categories


def test_run_reasoning_produces_multi_metric_chain(db_session):
    _seed_minimal_relationships(db_session)
    state = {"soil": {"organic_carbon": 0.3}, "climate": {"rainfall": "low"}, "land_use": "monoculture wheat"}
    result = run_reasoning(db_session, state)
    assert len(result["triggered_conditions"]) >= 3
    assert result["reasoning_chain"].is_multi_metric(min_metrics=3)
    assert len(result["intervention_categories"]) > 0


def test_run_reasoning_empty_state_no_triggers(db_session):
    _seed_minimal_relationships(db_session)
    result = run_reasoning(db_session, {})
    assert result["triggered_conditions"] == []
    assert result["intervention_categories"] == []
