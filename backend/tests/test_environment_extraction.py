from app.services.conversation import (
    detect_missing_fields,
    empty_state,
    extract_from_text,
    merge_structured_input,
    merge_updates,
    state_completeness,
)


def test_extract_organic_carbon_and_rainfall():
    text = "Soil organic carbon is 0.3% and rainfall is low. I grow monoculture wheat in a semi-arid region."
    updates = extract_from_text(text)
    assert updates["soil.organic_carbon"] == 0.3
    assert updates["climate.rainfall"] == "low"
    assert updates["land_use"] == "monoculture"
    assert updates["crop"] == "wheat"
    assert updates["location.region"] == "semi-arid"


def test_extract_ph():
    updates = extract_from_text("The soil pH is 7.5 here.")
    assert updates["soil.ph"] == 7.5


def test_merge_updates_nested():
    state = empty_state()
    state = merge_updates(state, {"soil.organic_carbon": 0.4, "climate.rainfall": "low"})
    assert state["soil"]["organic_carbon"] == 0.4
    assert state["climate"]["rainfall"] == "low"


def test_merge_structured_input_deep():
    state = empty_state()
    state = merge_structured_input(state, {"soil": {"ph": 6.8}, "land_use": "monoculture"})
    assert state["soil"]["ph"] == 6.8
    assert state["land_use"] == "monoculture"
    # unrelated fields remain untouched
    assert state["soil"]["organic_carbon"] is None


def test_missing_fields_detects_core_gaps():
    state = empty_state()
    missing = detect_missing_fields(state)
    assert len(missing) == 4  # all CORE_FIELDS missing


def test_missing_fields_shrinks_as_state_fills():
    state = empty_state()
    state = merge_updates(state, {"soil.organic_carbon": 0.3, "climate.rainfall": "low"})
    missing = detect_missing_fields(state)
    assert len(missing) == 2


def test_state_completeness_increases_with_fields():
    state = empty_state()
    c0 = state_completeness(state)
    state = merge_updates(state, {"soil.organic_carbon": 0.3, "climate.rainfall": "low", "land_use": "monoculture"})
    c1 = state_completeness(state)
    assert c1 > c0
