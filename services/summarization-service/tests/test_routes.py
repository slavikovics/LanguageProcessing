import pytest
from fastapi.testclient import TestClient
from nlp_core import tokenization

from app.main import app

client = TestClient(app)

_TEXT = (
    "Lasers are devices that emit light through optical amplification. "
    "A red laser and a blue laser differ mainly in wavelength.\n\n"
    "Laser devices are used in many fields such as medicine and industry. "
    "Industrial cutting lasers require careful safety handling."
)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _model_available() -> bool:
    try:
        tokenization.get_pipeline()
        return True
    except RuntimeError:
        return False


pytestmark = pytest.mark.skipif(
    not _model_available(), reason="en_core_web_sm model not installed"
)


def test_summarize_algorithmic_returns_selected_in_original_order():
    response = client.post(
        "/summarize/algorithmic",
        json={
            "text": _TEXT,
            "term_weights": {"laser": 3.0, "device": 1.5, "industrial": 2.0},
            "sentence_count": 2,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_sentences"] == 4
    assert len(body["selected"]) == 2
    assert [s["index"] for s in body["selected"]] == sorted(s["index"] for s in body["selected"])


def test_summarize_textrank_returns_requested_count():
    response = client.post(
        "/summarize/textrank", json={"text": _TEXT, "sentence_count": 3}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["selected"]) == 3


def test_summarize_embeddings_picks_sentence_closest_to_centroid():
    response = client.post(
        "/summarize/embeddings",
        json={
            "sentences": ["a", "b", "c"],
            "embeddings": [[1.0, 0.0], [0.0, 1.0], [0.6, 0.6]],
            "sentence_count": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["selected"][0]["index"] == 2


def test_summarize_embeddings_with_query_picks_sentence_closest_to_query():
    response = client.post(
        "/summarize/embeddings",
        json={
            "sentences": ["a", "b", "c"],
            "embeddings": [[1.0, 0.0], [0.0, 1.0], [0.6, 0.6]],
            "sentence_count": 1,
            "query_embedding": [0.0, 1.0],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["selected"][0]["index"] == 1


def test_keywords_hierarchy_returns_roots_with_matching_phrases():
    response = client.post(
        "/keywords/hierarchy",
        json={
            "text": _TEXT,
            "term_weights": {"laser": 3.0, "device": 1.5, "red": 1.0, "blue": 1.0},
            "top_n": 2,
        },
    )
    assert response.status_code == 200
    groups = response.json()["groups"]
    assert [g["term"] for g in groups] == ["laser", "device"]
    for group in groups:
        for child in group["children"]:
            assert group["term"] in child.split(" ")
