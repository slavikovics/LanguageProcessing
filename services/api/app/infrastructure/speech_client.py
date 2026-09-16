from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from app.core.config import get_settings


class SpeechServiceError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


# Generous 150s ceiling: exceeds faster-whisper's worst-case decode time so errors surface from speech-service, not timeout.
_STT_TIMEOUT_SECONDS = 150.0


class SpeechServiceClient:
    def __init__(self, base_url: str | None = None, *, timeout: float = 120.0) -> None:
        self._base_url = base_url or get_settings().speech_service_url
        self._timeout = timeout

    async def open_synthesis_stream(
        self, text: str, *, backend: str, voice: str | None, rate: float
    ) -> AsyncIterator[bytes]:
        client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        request = client.build_request(
            "POST",
            "/tts",
            json={"text": text, "backend": backend, "voice": voice, "rate": rate},
        )
        response = await client.send(request, stream=True)
        if response.status_code >= 400:
            body = await response.aread()
            await response.aclose()
            await client.aclose()
            raise SpeechServiceError(response.status_code, body.decode("utf-8", errors="replace"))

        async def _chunks() -> AsyncIterator[bytes]:
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        return _chunks()

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        content_type: str,
        backend: str,
        language: str | None,
        initial_prompt: str | None = None,
        vad_filter: bool = False,
        use_stream_model: bool = False,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        data = {"backend": backend}
        if language:
            data["language"] = language
        if initial_prompt:
            data["initial_prompt"] = initial_prompt
        if vad_filter:
            data["vad_filter"] = "true"
        if use_stream_model:
            data["use_stream_model"] = "true"
        async with httpx.AsyncClient(
            base_url=self._base_url, timeout=timeout or _STT_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(
                "/stt",
                files={"audio": (filename, audio_bytes, content_type)},
                data=data,
            )
            if response.status_code >= 400:
                raise SpeechServiceError(response.status_code, response.text)
            return response.json()
