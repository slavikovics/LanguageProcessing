from fastapi.testclient import TestClient

from app import model
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_translate_returns_model_output(monkeypatch):
    def fake_translate_batch(sentences: list[str]) -> list[str]:
        assert sentences == ["The cat sits.", "Dogs bark."]
        return ["Le chat est assis.", "Les chiens aboient."]

    monkeypatch.setattr(model, "translate_batch", fake_translate_batch)

    response = client.post("/translate", json={"sentences": ["The cat sits.", "Dogs bark."]})
    assert response.status_code == 200
    assert response.json()["translations"] == ["Le chat est assis.", "Les chiens aboient."]


def test_translate_empty_sentences_returns_empty_list():
    response = client.post("/translate", json={"sentences": []})
    assert response.status_code == 200
    assert response.json()["translations"] == []
