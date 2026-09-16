from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import SpeechBackend

# Must match speech-service's MAX_TTS_TEXT_LENGTH so oversized text is rejected before the network call.
MAX_TTS_TEXT_LENGTH = 5000


class SynthesizeSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_TEXT_LENGTH)
    backend: SpeechBackend = SpeechBackend.LOCAL
    voice: str | None = None
    rate: float = 1.0


class SpeechCommandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phrase: str
    action: str
    language: str
    is_active: bool
    created_at: dt.datetime


class TranscribeSpeechResponseOut(BaseModel):
    transcript: str
    detected_language: str | None
    backend_used: str
    elapsed_ms: float
    matched_command: SpeechCommandOut | None = None


class SpeechCommandCreate(BaseModel):
    phrase: str
    action: str
    language: str = "en"
    is_active: bool = True


class SpeechCommandUpdate(BaseModel):
    phrase: str | None = None
    action: str | None = None
    language: str | None = None
    is_active: bool | None = None
