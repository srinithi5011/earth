from app.services.evidence import strip_unverified_numbers, verify_recommendation
from app.services.retrieval import RetrievedChunk


def _chunk(text, relevance=0.5, credibility_tier="authoritative"):
    return RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        text=text,
        title="Test",
        organization="Test Org",
        source_url="https://example.org",
        publication_year=2024,
        document_type="report",
        topic="soil",
        region=None,
        credibility_tier=credibility_tier,
        similarity=relevance,
        relevance=relevance,
    )


def test_verify_recommendation_fails_with_no_evidence():
    rec = {"recommendation": "Do something.", "affected_metrics": []}
    result = verify_recommendation(rec, [])
    assert result["supported"] is False
    assert any("no evidence" in issue for issue in result["issues"])


def test_verify_recommendation_passes_with_supporting_evidence():
    chunk = _chunk("Cover crops increase soil organic carbon over multiple years.", relevance=0.5)
    rec = {"recommendation": "Introduce cover crops to increase soil organic carbon.", "affected_metrics": ["soil_organic_carbon"]}
    result = verify_recommendation(rec, [chunk])
    assert result["supported"] is True


def test_verify_recommendation_flags_unverified_numeric_claim():
    chunk = _chunk("Cover crops increase soil organic carbon over multiple years.", relevance=0.5)
    rec = {"recommendation": "This increases soil organic carbon by 47%.", "affected_metrics": []}
    result = verify_recommendation(rec, [chunk])
    assert result["supported"] is False
    assert any("47" in issue for issue in result["issues"])


def test_verify_recommendation_allows_numeric_claim_present_in_evidence():
    chunk = _chunk("Studies show a 25% increase in organic carbon over three years.", relevance=0.5)
    rec = {"recommendation": "This can increase organic carbon by 25% over three years.", "affected_metrics": []}
    result = verify_recommendation(rec, [chunk])
    assert result["supported"] is True


def test_strip_unverified_numbers_replaces_invented_percentage():
    chunk = _chunk("No numeric figures here at all.")
    text = "This will improve biodiversity by 30%."
    cleaned = strip_unverified_numbers(text, [chunk])
    assert "30%" not in cleaned
    assert "unavailable" in cleaned.lower()


def test_strip_unverified_numbers_keeps_verified_percentage():
    chunk = _chunk("The intervention showed a 25% improvement in trials.")
    text = "This can lead to a 25% improvement."
    cleaned = strip_unverified_numbers(text, [chunk])
    assert "25%" in cleaned
