from nlp_core import frequent_words

EN_CORPUS = [
    "The quick brown fox jumps over the lazy dog. The dog barks at the fox. "
    "It is a sunny day and the weather is nice. The dog and the fox are friends."
] * 3

FR_CORPUS = [
    "Le renard brun rapide saute par-dessus le chien paresseux. Le chien aboie "
    "sur le renard. C'est une belle journée et le temps est agréable."
] * 3


def test_build_profile_ranks_most_frequent_words_first():
    profile = frequent_words.build_profile(EN_CORPUS, top_n=5)
    assert profile[0] == "the"


def test_build_profile_respects_top_n():
    assert len(frequent_words.build_profile(EN_CORPUS, top_n=3)) == 3


def test_out_of_place_distance_is_lower_for_matching_language():
    en_profile = frequent_words.build_profile(EN_CORPUS, top_n=50)
    fr_profile = frequent_words.build_profile(FR_CORPUS, top_n=50)
    test_document = "The dog and the fox play in the sun near the weather station."

    assert frequent_words.out_of_place_distance(en_profile, test_document) < (
        frequent_words.out_of_place_distance(fr_profile, test_document)
    )


def test_out_of_place_distance_charges_max_penalty_for_missing_word():
    profile = ["zzzznotinanytext"]
    assert frequent_words.out_of_place_distance(profile, "completely unrelated text", max_penalty=42) == 42
