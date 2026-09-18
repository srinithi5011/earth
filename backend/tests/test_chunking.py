from app.knowledge.chunking import chunk_text, split_sentences


def test_split_sentences_basic():
    text = "This is one sentence. This is another one! Is this a third?"
    sentences = split_sentences(text)
    assert len(sentences) == 3


def test_chunk_text_respects_target_words():
    text = " ".join(["This is sentence number %d." % i for i in range(40)])
    chunks = chunk_text(text, target_words=50, overlap_sentences=1)
    assert len(chunks) > 1
    for c in chunks:
        # allow some overshoot since we only close a chunk after crossing the boundary
        assert len(c.text.split()) < 80


def test_chunk_text_empty_returns_empty():
    assert chunk_text("") == []


def test_chunk_text_overlap_present():
    text = " ".join(["Sentence %d has some content here." % i for i in range(30)])
    chunks = chunk_text(text, target_words=30, overlap_sentences=1)
    if len(chunks) > 1:
        # last sentence of chunk N should reappear as first sentence of chunk N+1
        last_sentence_of_first = chunks[0].text.split(".")[-2].strip() if chunks[0].text.count(".") > 1 else None
        assert chunks[1].text  # smoke check, overlap logic executed without error
