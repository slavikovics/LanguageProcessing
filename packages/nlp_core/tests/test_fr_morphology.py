from nlp_core import fr_morphology


def test_agree_adjective_regular():
    assert fr_morphology.agree_adjective("grand", "m", "Sing") == "grand"
    assert fr_morphology.agree_adjective("grand", "f", "Sing") == "grande"
    assert fr_morphology.agree_adjective("grand", "m", "Plur") == "grands"
    assert fr_morphology.agree_adjective("grand", "f", "Plur") == "grandes"


def test_agree_adjective_number_invariant():
    assert fr_morphology.agree_adjective("gris", "m", "Sing") == "gris"
    assert fr_morphology.agree_adjective("gris", "m", "Plur") == "gris"
    assert fr_morphology.agree_adjective("gris", "f", "Sing") == "grise"


def test_agree_adjective_irregular():
    assert fr_morphology.agree_adjective("beau", "m", "Sing") == "beau"
    assert fr_morphology.agree_adjective("beau", "f", "Sing") == "belle"
    assert fr_morphology.agree_adjective("beau", "m", "Plur") == "beaux"
    assert fr_morphology.agree_adjective("beau", "f", "Plur") == "belles"


def test_agree_adjective_unknown_word_passes_through_unchanged():
    assert fr_morphology.agree_adjective("zzznonexistentadj", "f", "Plur") == "zzznonexistentadj"


def test_pluralize_noun_regular():
    assert fr_morphology.pluralize_noun("chien") == "chiens"


def test_pluralize_noun_irregular():
    assert fr_morphology.pluralize_noun("cheval") == "chevaux"
    assert fr_morphology.pluralize_noun("chapeau") == "chapeaux"


def test_pluralize_noun_number_invariant():
    assert fr_morphology.pluralize_noun("prix") == "prix"


def test_pluralize_noun_unknown_word_passes_through_unchanged():
    assert fr_morphology.pluralize_noun("zzznonexistentnoun") == "zzznonexistentnoun"


def test_conjugate_verb_regular_er_present():
    assert fr_morphology.conjugate_verb("montrer", "3", "Sing") == "montre"
    assert fr_morphology.conjugate_verb("montrer", "1", "Plur") == "montrons"


def test_conjugate_verb_defaults_to_third_singular():
    assert fr_morphology.conjugate_verb("montrer", None, None) == "montre"


def test_conjugate_verb_irregular():
    assert fr_morphology.conjugate_verb("être", "1", "Sing") == "suis"
    assert fr_morphology.conjugate_verb("être", "3", "Plur") == "sont"
    assert fr_morphology.conjugate_verb("prendre", "3", "Sing") == "prend"


def test_conjugate_verb_unknown_word_passes_through_unchanged():
    assert fr_morphology.conjugate_verb("zzznonexistentverb", "3", "Sing") == "zzznonexistentverb"


def test_guess_gender_known_words():
    assert fr_morphology.guess_gender("complication") == "f"
    assert fr_morphology.guess_gender("traitement") == "m"


def test_guess_gender_lexicon_beats_naive_suffix_pattern():
    assert fr_morphology.guess_gender("couleur") == "f"
    assert fr_morphology.guess_gender("peinture") == "f"


def test_guess_gender_unknown_word_defaults_to_masculine():
    assert fr_morphology.guess_gender("zzznonexistentnoun") == "m"
