from app.domain.speech_streaming import StreamSession


def test_append_chunk_accumulates_full_text():
    session = StreamSession()
    assert session.append_chunk("hello there") == "hello there"
    assert session.append_chunk("how are you") == "hello there how are you"


def test_append_chunk_skips_empty_transcript():
    session = StreamSession()
    session.append_chunk("hello")
    assert session.append_chunk("   ") == "hello"
    assert session.append_chunk("") == "hello"


def test_append_chunk_normalizes_internal_whitespace():
    session = StreamSession()
    session.append_chunk("hello   there\n\n")
    assert session.full_text == "hello there"


def test_context_tail_returns_none_before_any_chunk():
    session = StreamSession()
    assert session.context_tail() is None


def test_context_tail_returns_trailing_slice():
    session = StreamSession()
    session.append_chunk("a" * 300)
    assert session.context_tail(max_chars=50) == ("a" * 300)[-50:]
