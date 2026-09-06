import pytest

from nlp_core import tokenization

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


def test_tokenize_lowercases_and_drops_stopwords_and_punctuation():
    words = [t.text for t in tokenization.tokenize("The cats are running, quickly!")]
    assert "the" not in words
    assert "are" not in words
    assert "cats" in words
    assert "running" in words
    assert "quickly" in words


def test_lemmatize_reduces_inflected_forms():
    lemmas = tokenization.lemmatize("The cats were running")
    assert "cat" in lemmas
    assert "run" in lemmas


def test_lemmatize_many_matches_lemmatize_per_text():
    texts = ["The cats were running", "Dogs bark loudly", ""]
    assert tokenization.lemmatize_many(texts) == [tokenization.lemmatize(t) for t in texts]


def test_lemmatize_many_empty_input():
    assert tokenization.lemmatize_many([]) == []


def test_clean_html_strips_tags_and_scripts():
    html = "<html><body><script>evil()</script><p>Hello <b>world</b></p></body></html>"
    assert tokenization.clean_html(html) == "Hello world"


def test_split_sentences_splits_on_boundaries():
    assert tokenization.split_sentences("Cats run. Dogs bark!") == ["Cats run.", "Dogs bark!"]


def test_char_ngrams_are_padded_with_spaces():
    assert " cat " in tokenization.char_ngrams("cat", n=5)
