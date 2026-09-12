import math

from nlp_core import weighting


def test_document_frequencies_counts_documents_not_occurrences():
    docs = [["cat", "cat", "dog"], ["dog", "fish"], ["cat"]]
    df = weighting.document_frequencies(docs)
    assert df == {"cat": 2, "dog": 2, "fish": 1}


def test_inverse_document_frequency_matches_formula_1_5():
    idf = weighting.inverse_document_frequency({"cat": 2}, total_documents=4)
    assert math.isclose(idf["cat"], math.log(4 / 2))


def test_inverse_document_frequency_rejects_empty_collection():
    try:
        weighting.inverse_document_frequency({"cat": 1}, total_documents=0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for total_documents=0")


def test_term_weights_matches_formula_1_6():
    tf = {"cat": 3}
    idf = {"cat": 2.0}
    assert weighting.term_weights(tf, idf) == {"cat": 6.0}


def test_term_weights_defaults_unknown_terms_to_zero_idf():
    weights = weighting.term_weights({"cat": 3}, {})
    assert weights == {"cat": 0.0}


def test_normalized_tfidf_vector_is_unit_length_when_nonzero():
    tf = {"cat": 3, "dog": 1}
    idf = {"cat": 2.0, "dog": 1.0}
    vector = weighting.normalized_tfidf_vector(tf, idf)
    norm = math.sqrt(sum(weight * weight for weight in vector.values()))
    assert math.isclose(norm, 1.0)


def test_normalized_tfidf_vector_handles_all_zero_weights():
    vector = weighting.normalized_tfidf_vector({"cat": 1}, {})
    assert vector == {"cat": 0.0}


def test_binary_query_vector_deduplicates_terms():
    vector = weighting.binary_query_vector(["cat", "dog", "cat"])
    assert vector == {"cat": 1.0, "dog": 1.0}


def test_modified_term_weight_matches_lr3_formula():
    weight = weighting.modified_term_weight(tf=3, tf_max=4, document_frequency=2, total_documents=8)
    assert math.isclose(weight, 0.5 * (1 + 3 / 4) * math.log(8 / 2))


def test_modified_term_weight_rejects_non_positive_tf_max():
    try:
        weighting.modified_term_weight(tf=1, tf_max=0, document_frequency=1, total_documents=1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for tf_max<=0")


def test_modified_term_weight_rejects_non_positive_document_frequency_or_total():
    try:
        weighting.modified_term_weight(tf=1, tf_max=1, document_frequency=0, total_documents=1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for document_frequency<=0")
