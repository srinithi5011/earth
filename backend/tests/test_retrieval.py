from app.knowledge.chunking import chunk_text
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.embeddings import cosine_similarity, get_embedding_backend
from app.services.retrieval import retrieve


def _seed_chunks(db):
    doc = KnowledgeDocument(
        title="Soil Carbon Test Doc",
        organization="Test Org",
        publication_year=2024,
        source_url="https://example.org/doc",
        document_type="curated_summary",
        topic="soil",
        region=None,
        credibility_tier="authoritative",
        raw_text="soil organic carbon improves water retention",
    )
    db.add(doc)
    db.flush()

    texts = [
        "Soil organic carbon improves water retention and supports microbial diversity in agricultural soils.",
        "Monoculture cropping reduces habitat diversity and structural complexity for insects.",
        "Rainfall variability strongly affects water availability in semi-arid farming systems.",
    ]
    for i, t in enumerate(texts):
        db.add(
            KnowledgeChunk(
                document_id=doc.document_id,
                chunk_index=i,
                text=t,
                title=doc.title,
                organization=doc.organization,
                publication_year=doc.publication_year,
                source_url=doc.source_url,
                document_type=doc.document_type,
                topic="soil" if i == 0 else ("biodiversity" if i == 1 else "climate"),
                region=None,
                credibility_tier="authoritative",
            )
        )
    db.flush()

    backend = get_embedding_backend()
    all_chunks = db.query(KnowledgeChunk).all()
    backend.fit([c.text for c in all_chunks])
    vectors = backend.embed([c.text for c in all_chunks])
    for c, v in zip(all_chunks, vectors):
        c.embedding = v
    db.commit()


def test_retrieve_returns_relevant_chunk_first(db_session):
    _seed_chunks(db_session)
    results = retrieve(db_session, "soil organic carbon water retention", top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    assert "soil" in results[0].text.lower() or "carbon" in results[0].text.lower()


def test_retrieve_metadata_filter_by_topic(db_session):
    _seed_chunks(db_session)
    results = retrieve(db_session, "diversity", top_k=5, topic="biodiversity", similarity_threshold=0.0)
    assert all(r.topic == "biodiversity" for r in results)


def test_retrieve_respects_similarity_threshold(db_session):
    _seed_chunks(db_session)
    results = retrieve(db_session, "completely unrelated automotive engine repair", top_k=5, similarity_threshold=0.5)
    assert results == []


def test_cosine_similarity_identical_vectors():
    v = [0.1, 0.2, 0.3]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1, 0], [0, 1]) == 0.0
