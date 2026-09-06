import math

import pytest
from fastapi.testclient import TestClient
from nlp_core import tokenization

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_idf_endpoint():
    response = client.post(
        "/idf", json={"document_term_lists": [["cat", "dog"], ["dog"], ["cat"]]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_documents"] == 3
    assert body["document_frequency"] == {"cat": 2, "dog": 2}
    assert math.isclose(body["idf"]["cat"], math.log(3 / 2))


def test_document_vector_endpoint_is_unit_length():
    response = client.post(
        "/document-vector",
        json={"term_frequencies": {"cat": 3, "dog": 1}, "idf": {"cat": 2.0, "dog": 1.0}},
    )
    assert response.status_code == 200
    vector = response.json()["vector"]
    norm = math.sqrt(sum(w * w for w in vector.values()))
    assert math.isclose(norm, 1.0)


def test_query_vector_endpoint():
    response = client.post("/query-vector", json={"terms": ["cat", "dog", "cat"]})
    assert response.status_code == 200
    assert response.json()["vector"] == {"cat": 1.0, "dog": 1.0}


def test_similarity_endpoint_identical_vectors():
    vec = {"cat": 0.6, "dog": 0.8}
    response = client.post("/similarity", json={"a": vec, "b": vec})
    assert response.status_code == 200
    assert math.isclose(response.json()["score"], 1.0)


def test_index_endpoint_computes_idf_and_unit_vectors():
    response = client.post(
        "/index",
        json={"document_term_lists": [["cat", "dog", "cat"], ["dog"], ["cat", "bird"]]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["term_frequencies"][0] == {"cat": 2, "dog": 1}
    assert math.isclose(body["idf"]["dog"], math.log(3 / 2))
    for vector in body["vectors"]:
        norm = math.sqrt(sum(w * w for w in vector.values()))
        assert math.isclose(norm, 1.0) or norm == 0.0


def test_idf_from_frequency_endpoint():
    response = client.post(
        "/idf-from-frequency",
        json={"document_frequency": {"cat": 2, "dog": 1}, "total_documents": 4},
    )
    assert response.status_code == 200
    idf = response.json()["idf"]
    assert math.isclose(idf["cat"], math.log(4 / 2))
    assert math.isclose(idf["dog"], math.log(4 / 1))


def test_metrics_evaluate_endpoint():
    response = client.post(
        "/metrics/evaluate",
        json={"ranked_ids": [1, 2, 3, 4], "relevant_ids": [1, 3]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["retrieved_count"] == 4
    assert body["relevant_count"] == 2
    assert math.isclose(body["precision"], 0.5)  # 2 hits / 4 retrieved
    assert math.isclose(body["recall"], 1.0)
    assert math.isclose(body["precision_at_5"], 0.4)  # 2 hits / 5 (n < 5 padding per definition)
    assert math.isclose(body["precision_at_10"], 0.2)
    assert math.isclose(body["r_precision"], 0.5)  # precision@|relevant_ids|=2 -> top 2 has 1 hit
    assert len(body["curve"]) == 11


def _model_available() -> bool:
    try:
        tokenization.get_pipeline()
        return True
    except RuntimeError:
        return False


@pytest.mark.skipif(not _model_available(), reason="en_core_web_sm model not installed")
def test_tokenize_endpoint():
    response = client.post("/tokenize", json={"text": "The cats are running quickly!"})
    assert response.status_code == 200
    words = [t["text"] for t in response.json()["tokens"]]
    assert "cats" in words
    assert "the" not in words
