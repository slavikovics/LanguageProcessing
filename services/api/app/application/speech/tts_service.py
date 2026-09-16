from __future__ import annotations

from typing import AsyncIterator

from app.infrastructure.speech_client import SpeechServiceClient


class SpeechSynthesisService:
    def __init__(self, *, client: SpeechServiceClient | None = None) -> None:
        self._client = client or SpeechServiceClient()

    async def stream(
        self, text: str, *, backend: str, voice: str | None, rate: float
    ) -> AsyncIterator[bytes]:
        return await self._client.open_synthesis_stream(
            text, backend=backend, voice=voice, rate=rate
        )
