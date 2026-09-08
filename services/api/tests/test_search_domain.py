import pytest

from app.domain.search import SearchError, build_search_query_config, build_snippet


def test_build_search_query_config_trims_and_defaults():
    config = build_search_query_config(collection_id=1, text="  machine learning  ", top_k=5)
    assert config.text == "machine learning"
    assert config.top_k == 5
    assert config.collection_id == 1


def test_build_search_query_config_rejects_empty_text():
    with pytest.raises(SearchError):
        build_search_query_config(collection_id=1, text="   ", top_k=10)


def test_build_search_query_config_rejects_out_of_range_top_k():
    with pytest.raises(SearchError):
        build_search_query_config(collection_id=1, text="cats", top_k=0)
    with pytest.raises(SearchError):
        build_search_query_config(collection_id=1, text="cats", top_k=101)


def test_build_snippet_centers_on_first_focus_word():
    text = "x" * 500 + " target word here " + "y" * 500
    snippet = build_snippet(text, ["target"], max_chars=60)
    assert "target" in snippet
    assert snippet.startswith("…")


def test_build_snippet_falls_back_to_start_when_no_match():
    text = "The quick brown fox jumps over the lazy dog."
    snippet = build_snippet(text, ["nonexistent"], max_chars=1000)
    assert snippet == text
    assert not snippet.startswith("…")


def test_build_snippet_truncates_long_text():
    text = "word " * 200
    snippet = build_snippet(text, [], max_chars=50)
    assert len(snippet) <= 52
    assert snippet.endswith("…")
