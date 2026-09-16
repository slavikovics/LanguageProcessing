import io

from fastapi.testclient import TestClient

from app import routes, stt_local, tts_local
from app.main import app
from app.schemas import MAX_TTS_TEXT_LENGTH

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tts_local_streams_backend_bytes(monkeypatch):
    def fake_stream(text, *, voice=None, rate=1.0):
        assert text == "hello"
        yield b"RIFF-FAKE-WAV-HEADER"
        yield b"more-audio-bytes"

    monkeypatch.setattr(tts_local, "synthesize_stream", fake_stream)

    response = client.post("/tts", json={"text": "hello", "backend": "local"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"RIFF-FAKE-WAV-HEADERmore-audio-bytes"


def test_tts_unknown_backend_returns_422():
    response = client.post("/tts", json={"text": "hello", "backend": "carrier-pigeon"})
    assert response.status_code == 422


def test_tts_text_over_max_length_returns_422():
    response = client.post(
        "/tts", json={"text": "a" * (MAX_TTS_TEXT_LENGTH + 1), "backend": "local"}
    )
    assert response.status_code == 422


def test_tts_empty_text_returns_422():
    response = client.post("/tts", json={"text": "", "backend": "local"})
    assert response.status_code == 422


def test_stt_local_returns_transcript(monkeypatch):
    def fake_transcribe(
        audio_bytes, *, language_hint=None, initial_prompt=None, vad_filter=False, use_stream_model=False
    ):
        assert audio_bytes == b"fake-audio-bytes"
        assert initial_prompt is None
        assert vad_filter is False
        assert use_stream_model is False
        return "hello world", "en"

    monkeypatch.setattr(stt_local, "transcribe", fake_transcribe)

    response = client.post(
        "/stt",
        data={"backend": "local"},
        files={"audio": ("test.wav", io.BytesIO(b"fake-audio-bytes"), "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "hello world"
    assert body["detected_language"] == "en"
    assert body["backend_used"] == "local"


def test_stt_local_forwards_streaming_fields(monkeypatch):
    def fake_transcribe(
        audio_bytes, *, language_hint=None, initial_prompt=None, vad_filter=False, use_stream_model=False
    ):
        assert initial_prompt == "previous words"
        assert vad_filter is True
        assert use_stream_model is True
        return "more words", "en"

    monkeypatch.setattr(stt_local, "transcribe", fake_transcribe)

    response = client.post(
        "/stt",
        data={
            "backend": "local",
            "initial_prompt": "previous words",
            "vad_filter": "true",
            "use_stream_model": "true",
        },
        files={"audio": ("chunk.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json()["transcript"] == "more words"


def test_stt_unknown_backend_returns_422():
    response = client.post(
        "/stt",
        data={"backend": "carrier-pigeon"},
        files={"audio": ("test.wav", io.BytesIO(b"data"), "audio/wav")},
    )
    assert response.status_code == 422


def test_stt_oversized_audio_returns_413(monkeypatch):
    monkeypatch.setattr(routes, "MAX_AUDIO_UPLOAD_BYTES", 10)

    def fake_transcribe(audio_bytes, *, language_hint=None):
        raise AssertionError("whisper should never be reached for oversized audio")

    monkeypatch.setattr(stt_local, "transcribe", fake_transcribe)

    response = client.post(
        "/stt",
        data={"backend": "local"},
        files={"audio": ("test.wav", io.BytesIO(b"x" * 1000), "audio/wav")},
    )
    assert response.status_code == 413
