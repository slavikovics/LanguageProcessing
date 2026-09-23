import pytest

from nlp_core import syntax_parsing, transfer_translation, translation

pytest.importorskip("spacy")


def _model_available() -> bool:
    try:
        syntax_parsing.get_parser_pipeline()
        return True
    except RuntimeError:
        return False


pytestmark = pytest.mark.skipif(
    not _model_available(), reason="en_core_web_sm model not installed"
)

_LOOKUP = {
    translation.dictionary_key("trial", "NOUN"): "essai",
    translation.dictionary_key("serious", "ADJ"): "grave",
    translation.dictionary_key("complication", "NOUN"): "complication",
    translation.dictionary_key("show", "VERB"): "montrer",
    translation.dictionary_key("patient", "NOUN"): "patient",
    translation.dictionary_key("symptom", "NOUN"): "symptôme",
    translation.dictionary_key("treatment", "NOUN"): "traitement",
    translation.dictionary_key("disease", "NOUN"): "maladie",
    translation.dictionary_key("improve", "VERB"): "améliorer",
    translation.dictionary_key("good", "ADJ"): "bon",
    translation.dictionary_key("idea", "NOUN"): "idée",
    translation.dictionary_key("the", "DET"): "le",
    translation.dictionary_key("a", "DET"): "un",
    translation.dictionary_key("of", "ADP"): "de",
    translation.dictionary_key("cat", "NOUN"): "chat",
}


def test_adjective_moves_after_noun():
    result = transfer_translation.transfer_translate("The trial has a serious complication.", _LOOKUP)
    assert "complication grave" in result.translated_text
    assert "grave complication" not in result.translated_text


def test_prenominal_adjective_exception_keeps_order():
    result = transfer_translation.transfer_translate("A good idea.", _LOOKUP)
    assert "bonne idée" in result.translated_text.lower()
    assert "idée bonne" not in result.translated_text.lower()


def test_negation_produces_ne_pas_and_drops_do_support():
    result = transfer_translation.transfer_translate("The patient does not show symptoms.", _LOOKUP)
    assert "ne montre pas" in result.translated_text.lower()
    assert "does" not in result.translated_text.lower()


def test_negation_elides_ne_before_vowel():
    result = transfer_translation.transfer_translate("The trial does not improve.", _LOOKUP)
    assert "n'améliore pas" in result.translated_text.lower()


def test_preposition_contracts_with_article():
    result = transfer_translation.transfer_translate("The treatment of the disease.", _LOOKUP)
    assert "du maladie" in result.translated_text.lower() or "du " in result.translated_text.lower()
    assert "de le" not in result.translated_text.lower()


def test_unknown_words_pass_through_untouched():
    result = transfer_translation.transfer_translate("The dog barks.", _LOOKUP)
    assert "dog" in result.translated_text
    assert result.word_count == 3
    assert result.translated_word_count == 1


def test_plain_sentence_matches_word_for_word_when_no_rule_triggers():
    result = transfer_translation.transfer_translate("The cat.", _LOOKUP)
    assert result.translated_text.rstrip(".").strip() == "Le chat"


def test_sentence_final_punctuation_stays_tight_after_reordering():
    result = transfer_translation.transfer_translate("The trial has a serious complication.", _LOOKUP)
    assert " ." not in result.translated_text
    assert result.translated_text.endswith(".")


def test_hyphenated_compound_stays_tight():
    lookup = {**_LOOKUP, translation.dictionary_key("war", "NOUN"): "guerre"}
    result = transfer_translation.transfer_translate("A post-war trial.", lookup)
    assert " - " not in result.translated_text
    assert "-" in result.translated_text


def test_ellipsis_has_no_leading_space():
    result = transfer_translation.transfer_translate("The trial improves...", _LOOKUP)
    assert " ..." not in result.translated_text
    assert result.translated_text.endswith("...")


def test_quotes_bind_to_their_words_not_the_gap():
    result = transfer_translation.transfer_translate('The patient said "good".', _LOOKUP)
    assert ' "' in result.translated_text  # space before the opening quote (normal word gap)
    assert '" ' not in result.translated_text  # but nothing pries the quotes apart from their word


def test_adjective_agrees_with_feminine_noun():
    result = transfer_translation.transfer_translate("A good idea.", _LOOKUP)
    assert "bonne idée" in result.translated_text.lower()
    assert "bon idée" not in result.translated_text.lower()


def test_adjective_and_noun_agree_with_plural():
    lookup = {
        **_LOOKUP,
        translation.dictionary_key("big", "ADJ"): "grand",
        translation.dictionary_key("dog", "NOUN"): "chien",
    }
    result = transfer_translation.transfer_translate("The big dogs.", lookup)
    assert "grands chiens" in result.translated_text.lower()


def test_verb_agrees_with_person_and_number():
    result = transfer_translation.transfer_translate("The patient shows symptoms.", _LOOKUP)
    assert "montre " in result.translated_text.lower()
    assert "montrer" not in result.translated_text.lower()


def test_agreement_is_noop_when_word_has_no_translation():
    result = transfer_translation.transfer_translate("The big dogs.", _LOOKUP)
    assert "dog" in result.translated_text.lower()
