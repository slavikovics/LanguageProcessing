import math

import pytest

from nlp_core import summarization, tokenization

pytest.importorskip("spacy")


def _model_available() -> bool:
    try:
        tokenization.get_pipeline()
        return True
    except RuntimeError:
        return False


pytestmark = pytest.mark.skipif(
    not _model_available(), reason="en_core_web_sm model not installed"
)

_TEXT = (
    "Lasers are devices that emit light through optical amplification. "
    "A red laser and a blue laser differ mainly in wavelength.\n\n"
    "Laser devices are used in many fields such as medicine and industry. "
    "Industrial cutting lasers require careful safety handling."
)


def test_split_paragraphs_splits_on_blank_lines():
    paragraphs = summarization.split_paragraphs(_TEXT)
    assert len(paragraphs) == 2
    assert paragraphs[0].startswith("Lasers are devices")
    assert paragraphs[1].startswith("Laser devices are used")


def test_split_sentences_with_positions_covers_all_sentences():
    spans = summarization.split_sentences_with_positions(_TEXT)
    assert len(spans) == 4
    assert spans[0].text.startswith("Lasers are devices")
    assert spans[0].doc_start == _TEXT.find(spans[0].text)
    assert spans[0].paragraph_start == 0


def test_sentence_document_position_weight_decreases_toward_end_of_document():
    early = summarization.sentence_document_position_weight(0, 100)
    late = summarization.sentence_document_position_weight(90, 100)
    assert early > late
    assert math.isclose(early, 1.0)


def test_sentence_paragraph_position_weight_handles_empty_paragraph():
    assert summarization.sentence_paragraph_position_weight(0, 0) == 1.0


def test_modified_tfidf_sentence_score_matches_formula():
    weights = {"laser": 2.0, "red": 1.0}
    score = summarization.modified_tfidf_sentence_score(["laser", "laser", "red"], weights)
    assert score == 2 * 2.0 + 1 * 1.0


def test_rank_sentences_algorithm_scores_every_sentence_once():
    term_weights = {"laser": 3.0, "device": 1.5, "cut": 1.0}
    scores = summarization.rank_sentences_algorithm(_TEXT, term_weights)
    assert len(scores) == 4
    assert all(isinstance(s.weight, float) for s in scores)


def test_rank_sentences_textrank_is_probability_like_and_converges():
    scores = summarization.rank_sentences_textrank(_TEXT)
    assert len(scores) == 4
    assert all(s.weight > 0 for s in scores)


def test_rank_sentences_textrank_single_sentence_gets_full_weight():
    scores = summarization.rank_sentences_textrank("Cats run.")
    assert scores == [summarization.SentenceScore(index=0, text="Cats run.", weight=1.0)]


def test_rank_sentences_by_embedding_centrality_prefers_sentence_closest_to_centroid():
    sentences = ["a", "b", "c"]
    embeddings = [[1.0, 0.0], [0.0, 1.0], [0.6, 0.6]]
    scores = summarization.rank_sentences_by_embedding_centrality(sentences, embeddings)
    best = max(scores, key=lambda s: s.weight)
    assert best.index == 2


def test_rank_sentences_by_embedding_centrality_rejects_length_mismatch():
    with pytest.raises(ValueError):
        summarization.rank_sentences_by_embedding_centrality(["a", "b"], [[1.0, 0.0]])


def test_select_summary_sentences_returns_top_n_in_original_order():
    scores = [
        summarization.SentenceScore(index=0, text="s0", weight=0.1),
        summarization.SentenceScore(index=1, text="s1", weight=0.9),
        summarization.SentenceScore(index=2, text="s2", weight=0.5),
    ]
    selected = summarization.select_summary_sentences(scores, target_count=2)
    assert [s.index for s in selected] == [1, 2]


def test_extract_keywords_from_weights_orders_by_weight_descending():
    weights = {"laser": 3.0, "device": 1.5, "cut": 5.0}
    assert summarization.extract_keywords_from_weights(weights, top_n=2) == ["cut", "laser"]


_HIERARCHY_TEXT = (
    "Red laser devices differ from blue laser devices. "
    "Industrial safety devices are essential."
)
_HIERARCHY_WEIGHTS = {
    "laser": 3.0,
    "device": 1.5,
    "red": 1.0,
    "blue": 1.0,
    "safety": 0.8,
    "industrial": 0.5,
}


def test_extract_keyword_hierarchy_orders_roots_by_weight():
    groups = summarization.extract_keyword_hierarchy(_HIERARCHY_WEIGHTS, _HIERARCHY_TEXT, top_n=2)
    assert [g.term for g in groups] == ["laser", "device"]


def test_extract_keyword_hierarchy_nests_phrases_under_their_root_and_avoids_duplicates():
    groups = summarization.extract_keyword_hierarchy(_HIERARCHY_WEIGHTS, _HIERARCHY_TEXT, top_n=2)
    all_children = [child for group in groups for child in group.children]

    # every child phrase actually contains the root term it was nested under
    for group in groups:
        for child in group.children:
            assert group.term in child.split(" ")

    # no phrase is assigned to more than one root
    assert len(all_children) == len(set(all_children))


def test_extract_keyword_hierarchy_returns_leaf_roots_when_no_phrases_match():
    weights = {"cat": 2.0, "dog": 1.0}
    groups = summarization.extract_keyword_hierarchy(weights, "Cats run. Dogs bark.", top_n=2)
    assert [g.term for g in groups] == ["cat", "dog"]
    assert all(g.children == [] for g in groups)


def test_extract_keyword_hierarchy_handles_empty_weights():
    assert summarization.extract_keyword_hierarchy({}, _HIERARCHY_TEXT) == []
