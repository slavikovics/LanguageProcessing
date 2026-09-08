
from nlp_core.tokenization import simple_word_tokenize


def test_lowercases_and_splits_on_whitespace_and_punctuation():
    assert simple_word_tokenize("The Quick, Brown Fox!") == ["the", "quick", "brown", "fox"]


def test_keeps_accented_letters():
    assert simple_word_tokenize("Le café est déjà prêt à Noël") == [
        "le",
        "café",
        "est",
        "déjà",
        "prêt",
        "à",
        "noël",
    ]


def test_keeps_apostrophes_inside_words():
    assert simple_word_tokenize("C'est aujourd'hui") == ["c'est", "aujourd'hui"]


def test_drops_digits():
    assert simple_word_tokenize("room101 costs 50 euros") == ["room", "costs", "euros"]


def test_empty_string_returns_empty_list():
    assert simple_word_tokenize("") == []
