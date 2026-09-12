import pytest

from nlp_core import tokenization, translation

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

_LOOKUP = {
    translation.dictionary_key("cat", "NOUN"): "chat",
    translation.dictionary_key("run", "VERB"): "courir",
    translation.dictionary_key("the", "DET"): "le",
}


def test_translate_replaces_known_words_and_preserves_punctuation():
    result = translation.translate("The cat runs.", _LOOKUP)
    assert result.translated_text == "Le chat courir."
    assert result.word_count == 3
    assert result.translated_word_count == 3


def test_translate_leaves_unknown_words_untouched():
    result = translation.translate("The dog barks.", _LOOKUP)
    assert "dog" in result.translated_text
    assert result.word_count == 3
    assert result.translated_word_count == 1


def test_translate_preserves_capitalisation():
    result = translation.translate("Cats.", _LOOKUP)
    assert result.translated_text.startswith("Chat")


def test_build_word_list_sorted_by_frequency_and_excludes_stopwords():
    words = translation.build_word_list("Cats chase cats. Cats run.", _LOOKUP)
    assert words[0].lemma == "cat"
    assert words[0].frequency == 3
    assert words[0].translation == "chat"
    assert all(word.lemma != "the" for word in words)
