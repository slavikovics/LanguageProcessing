import math

from nlp_core import alphabetic

EN_CORPUS = [
    "The quick brown fox jumps over the lazy dog. The dog barks at the fox. "
    "It is a sunny day and the weather is nice. The dog and the fox are friends."
] * 3

FR_CORPUS = [
    "Le renard brun rapide saute par-dessus le chien paresseux. Le chien aboie "
    "sur le renard. C'est une belle journée et le temps est agréable."
] * 3


def test_build_profile_normalizes_to_one():
    profile = alphabetic.build_profile(EN_CORPUS)
    assert math.isclose(sum(profile.values()), 1.0)


def test_build_profile_empty_text_returns_empty_profile():
    assert alphabetic.build_profile([""]) == {}


def test_build_profile_captures_accented_letters():
    profile = alphabetic.build_profile(["café à Noël"])
    assert "é" in profile and "à" in profile


def test_distance_is_lower_for_matching_language():
    en_profile = alphabetic.build_profile(EN_CORPUS)
    fr_profile = alphabetic.build_profile(FR_CORPUS)
    test_document = "The dog and the fox play in the sun near the weather station."

    assert alphabetic.distance(en_profile, test_document) < alphabetic.distance(fr_profile, test_document)


def test_distance_to_self_is_zero():
    profile = alphabetic.build_profile(EN_CORPUS)
    assert alphabetic.distance(profile, EN_CORPUS[0]) == 0.0
