from pydantic import BaseModel, Field

MAX_TTS_TEXT_LENGTH = 5000
# Bounds Piper's per-call cost; mirrors api service's SynthesizeSpeechRequest limit.


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_TEXT_LENGTH)
    backend: str = "local"
    voice: str | None = None
    rate: float = 1.0
    language: str | None = None


class TranscribeResponse(BaseModel):
    transcript: str
    detected_language: str | None
    backend_used: str
    elapsed_ms: float
