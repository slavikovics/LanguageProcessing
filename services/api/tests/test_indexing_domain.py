from app.domain.indexing import chunk_text


def test_chunk_text_short_document_is_one_chunk():
    text = "A short document about cats and dogs."
    assert chunk_text(text) == [text]


def test_chunk_text_empty_text_is_no_chunks():
    assert chunk_text("") == []


def test_chunk_text_splits_long_document_into_multiple_overlapping_chunks():
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)

    chunks = chunk_text(text, target_words=350, overlap_words=40)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.split()) <= 350


def test_chunk_text_covers_every_word_with_no_gaps():
    """Every word of the source document must appear in at least one
    chunk — chunking must never silently drop the tail of a long document
    (the whole point of chunking instead of truncating)."""
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)

    chunks = chunk_text(text, target_words=350, overlap_words=40)
    covered = set()
    for chunk in chunks:
        covered.update(chunk.split())

    assert covered == set(words)
    # The last chunk must reach all the way to the document's last word —
    # otherwise the tail is dropped even though earlier words are covered.
    assert chunks[-1].split()[-1] == words[-1]


def test_chunk_text_overlap_keeps_boundary_words_in_two_chunks():
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)

    chunks = chunk_text(text, target_words=350, overlap_words=40)

    # The word at the seam between chunk 0 and chunk 1 should appear in both.
    seam_word = words[349]
    assert seam_word in chunks[0].split()
    assert seam_word in chunks[1].split()
