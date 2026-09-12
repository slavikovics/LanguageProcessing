import pytest

from nlp_core import syntax_parsing

pytest.importorskip("spacy")


def _parser_available() -> bool:
    try:
        syntax_parsing.get_parser_pipeline()
        return True
    except RuntimeError:
        return False


pytestmark = pytest.mark.skipif(
    not _parser_available(), reason="en_core_web_sm model not installed"
)


def test_parse_sentence_finds_root_with_no_head():
    tokens = syntax_parsing.parse_sentence("The doctor examined the patient.")
    roots = [tok for tok in tokens if tok.head_position is None]
    assert len(roots) == 1
    assert roots[0].pos == "VERB"


def test_parse_sentence_head_positions_are_consistent():
    tokens = syntax_parsing.parse_sentence("The doctor examined the patient.")
    by_position = {tok.position: tok for tok in tokens}
    for tok in tokens:
        if tok.head_position is not None:
            assert tok.head_position in by_position
            assert by_position[tok.head_position].text == tok.head_text


def test_parse_sentence_keeps_punctuation_tokens():
    tokens = syntax_parsing.parse_sentence("Wait, really?")
    assert any(tok.is_punct for tok in tokens)
