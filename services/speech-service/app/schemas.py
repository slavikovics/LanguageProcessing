from pydantic import BaseModel, Field

MAX_TTS_TEXT_LENGTH = 5000
"""Piper synthesizes the whole string in one call, so an unbounded text
length turns into unbounded CPU/memory for the local backend — this caps it
to a size the container's resource limits (see docker-compose.yml) can
comfortably absorb. Mirrored in the api service's SynthesizeSpeechRequest."""


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
