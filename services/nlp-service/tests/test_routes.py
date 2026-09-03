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
