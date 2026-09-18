import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.knowledge.chunking import chunk_text
from app.main import app
from app.models.database import Base, get_db
from app.models.knowledge import EnvironmentalRelationship, KnowledgeChunk, KnowledgeDocument
from app.services.embeddings import get_embedding_backend

TEST_ENGINE = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=TEST_ENGINE)


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestSession()

    # Minimal relationship graph
    rels = [
        ("soil carbon", "increases", "water retention", "positive", "strong"),
        ("water retention", "increases", "plant resilience", "positive", "moderate"),
        ("monoculture", "reduces", "habitat diversity", "negative", "strong"),
        ("habitat diversity", "increases", "species richness", "positive", "strong"),
        ("rainfall", "increases", "water availability", "positive", "strong"),
    ]
    for s, r, t, d, strength in rels:
        db.add(EnvironmentalRelationship(source_metric=s, relationship=r, target_metric=t, direction=d, strength=strength))

    # Minimal knowledge corpus
    doc = KnowledgeDocument(
        title="Cover Crops and Soil Carbon",
        organization="Test Knowledge Base",
        publication_year=2024,
        source_url="https://example.org/cover-crops",
        document_type="curated_summary",
        topic="soil",
        credibility_tier="authoritative",
        raw_text="Legume cover crops increase soil organic carbon and improve water retention over multiple growing seasons.",
    )
    db.add(doc)
    db.flush()
    for c in chunk_text(doc.raw_text):
        db.add(
            KnowledgeChunk(
                document_id=doc.document_id,
                chunk_index=c.index,
                text=c.text,
                title=doc.title,
                organization=doc.organization,
                publication_year=doc.publication_year,
                source_url=doc.source_url,
                document_type=doc.document_type,
                topic=doc.topic,
                credibility_tier=doc.credibility_tier,
            )
        )
    db.commit()

    chunks = db.query(KnowledgeChunk).all()
    backend = get_embedding_backend()
    backend.fit([c.text for c in chunks])
    for c, v in zip(chunks, backend.embed([c.text for c in chunks])):
        c.embedding = v
    db.commit()
    db.close()

    yield


client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True  # no LLM_API_KEY configured in test env


def test_chat_asks_for_missing_information_on_vague_message():
    resp = client.post(
        "/api/chat",
        json={"session_id": "test-session-1", "message": "Biodiversity is declining on my land."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_more_information"] is True
    assert len(body["missing_fields"]) > 0


def test_chat_produces_recommendations_with_full_state():
    resp = client.post(
        "/api/chat",
        json={
            "session_id": "test-session-2",
            "message": "Soil organic carbon is 0.3%, rainfall is low, I grow monoculture wheat in a semi-arid region.",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_more_information"] is False
    assert len(body["drivers"]) >= 3
    assert len(body["relationships"]) > 0
    # Every recommendation must carry required structured fields (spec section 5)
    for rec in body["recommendations"]:
        assert "recommendation" in rec
        assert "scientific_reasoning" in rec
        assert "confidence_label" in rec


def test_analyze_endpoint_structured_input():
    payload = {
        "environmental_state": {
            "soil": {"organic_carbon": 0.3},
            "climate": {"rainfall": "low"},
            "land_use": "monoculture",
            "location": {"region": "semi-arid"},
        },
        "session_id": "test-analyze",
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_more_information"] is False


def test_evidence_endpoint_returns_seeded_chunks():
    resp = client.get("/api/evidence")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_relationships_endpoint_returns_graph():
    resp = client.get("/api/relationships")
    assert resp.status_code == 200
    assert len(resp.json()) >= 5


def test_conversation_persists_across_turns():
    r1 = client.post(
        "/api/chat", json={"session_id": "test-session-3", "message": "Soil organic carbon is 0.3%."}
    )
    conv_id = r1.json()["conversation_id"]
    r2 = client.post(
        "/api/chat",
        json={"session_id": "test-session-3", "conversation_id": conv_id, "message": "Rainfall is low, land use is monoculture, region is semi-arid."},
    )
    assert r2.json()["needs_more_information"] is False
    conv = client.get(f"/api/conversations/{conv_id}")
    assert conv.status_code == 200
    assert len(conv.json()["messages"]) >= 4  # 2 user + 2 assistant
