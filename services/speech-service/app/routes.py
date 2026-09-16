from __future__ import annotations

import time

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app import stt_local, tts_local
from app.schemas import SynthesizeRequest, TranscribeResponse

router = APIRouter(tags=["speech"])

MAX_AUDIO_UPLOAD_BYTES = 25 * 1024 * 1024
# Caps decode+transcribe cost; mirrors api service's /speech/stt limit.


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/tts")
async def synthesize(payload: SynthesizeRequest) -> StreamingResponse:
    if payload.backend != "local":
        raise HTTPException(status_code=422, detail=f"unknown backend: {payload.backend}")

    stream = tts_local.synthesize_stream(payload.text, voice=payload.voice, rate=payload.rate)
    return StreamingResponse(stream, media_type="audio/wav")


@router.post("/stt", response_model=TranscribeResponse)
async def transcribe(
    audio: UploadFile,
    backend: str = Form("local"),
    language: str | None = Form(None),
    initial_prompt: str | None = Form(None),
    vad_filter: bool = Form(False),
    use_stream_model: bool = Form(False),
) -> TranscribeResponse:
    started = time.perf_counter()
    audio_bytes = await _read_capped(audio, MAX_AUDIO_UPLOAD_BYTES)

    if backend != "local":
        raise HTTPException(status_code=422, detail=f"unknown backend: {backend}")

    # Offload to a thread: whisper's transcribe() is blocking and would stall the event loop.
    transcript, detected_language = await run_in_threadpool(
        stt_local.transcribe,
        audio_bytes,
        language_hint=language,
        initial_prompt=initial_prompt,
        vad_filter=vad_filter,
        use_stream_model=use_stream_model,
    )

    elapsed_ms = (time.perf_counter() - started) * 1000
    return TranscribeResponse(
        transcript=transcript,
        detected_language=detected_language,
        backend_used=backend,
        elapsed_ms=elapsed_ms,
    )


async def _read_capped(upload: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"audio upload exceeds {max_bytes} byte limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)
