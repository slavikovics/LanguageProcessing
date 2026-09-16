import asyncio
import json
import logging

import httpx
from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.speech import SpeechCommandService, SpeechRecognitionService, SpeechSynthesisService
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.domain.speech import SpeechCommandDef, SpeechError, match_command
from app.domain.speech_streaming import StreamSession
from app.infrastructure.repositories.speech import SpeechCommandRepository
from app.infrastructure.speech_client import SpeechServiceClient, SpeechServiceError
from app.interface.schemas import (
    SpeechCommandCreate,
    SpeechCommandOut,
    SpeechCommandUpdate,
    SynthesizeSpeechRequest,
    TranscribeSpeechResponseOut,
)

router = APIRouter(tags=["speech"])
logger = logging.getLogger(__name__)

# Must match speech-service's MAX_AUDIO_UPLOAD_BYTES to reject oversized uploads before proxying.
MAX_AUDIO_UPLOAD_BYTES = 25 * 1024 * 1024

# 20s ceiling for one stream chunk; batch /speech/stt route needs the larger 150s budget.
_STREAM_CHUNK_TIMEOUT_SECONDS = 20.0

# Caps concurrent speech-service requests across sessions to stay within container's cpus budget (docker-compose.yml).
_live_stt_semaphore = asyncio.Semaphore(get_settings().speech_stream_max_concurrency)


def _raise_for_speech_error(exc: SpeechError) -> None:
    status = 404 if "not found" in str(exc) else 422
    raise HTTPException(status_code=status, detail=str(exc)) from exc


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


@router.post("/speech/tts")
async def synthesize_speech(payload: SynthesizeSpeechRequest) -> StreamingResponse:
    service = SpeechSynthesisService()
    try:
        stream = await service.stream(
            payload.text, backend=payload.backend.value, voice=payload.voice, rate=payload.rate
        )
    except SpeechServiceError as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc
    return StreamingResponse(stream, media_type="audio/wav")


@router.post("/speech/stt", response_model=TranscribeSpeechResponseOut)
async def transcribe_speech(
    audio: UploadFile,
    backend: str = Form("local"),
    language: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> TranscribeSpeechResponseOut:
    service = SpeechRecognitionService(db)
    audio_bytes = await _read_capped(audio, MAX_AUDIO_UPLOAD_BYTES)
    try:
        outcome, matched = await service.transcribe(
            audio_bytes,
            filename=audio.filename or "audio.webm",
            content_type=audio.content_type or "audio/webm",
            backend=backend,
            language=language,
        )
    except SpeechServiceError as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc

    return TranscribeSpeechResponseOut(
        transcript=outcome.transcript,
        detected_language=outcome.detected_language,
        backend_used=outcome.backend_used,
        elapsed_ms=outcome.elapsed_ms,
        matched_command=SpeechCommandOut.model_validate(matched) if matched else None,
    )


@router.get("/speech/commands", response_model=list[SpeechCommandOut])
async def list_speech_commands(db: AsyncSession = Depends(get_db)) -> list[SpeechCommandOut]:
    service = SpeechCommandService(db)
    commands = await service.list_commands()
    return [SpeechCommandOut.model_validate(c) for c in commands]


@router.post("/speech/commands", response_model=SpeechCommandOut, status_code=201)
async def create_speech_command(
    payload: SpeechCommandCreate, db: AsyncSession = Depends(get_db)
) -> SpeechCommandOut:
    service = SpeechCommandService(db)
    command = await service.create_command(
        phrase=payload.phrase, action=payload.action, language=payload.language, is_active=payload.is_active
    )
    return SpeechCommandOut.model_validate(command)


@router.patch("/speech/commands/{command_id}", response_model=SpeechCommandOut)
async def update_speech_command(
    command_id: int, payload: SpeechCommandUpdate, db: AsyncSession = Depends(get_db)
) -> SpeechCommandOut:
    service = SpeechCommandService(db)
    try:
        command = await service.update_command(
            command_id, **payload.model_dump(exclude_unset=True)
        )
    except SpeechError as exc:
        _raise_for_speech_error(exc)
    return SpeechCommandOut.model_validate(command)


@router.delete("/speech/commands/{command_id}", status_code=204)
async def delete_speech_command(command_id: int, db: AsyncSession = Depends(get_db)) -> None:
    service = SpeechCommandService(db)
    try:
        await service.delete_command(command_id)
    except SpeechError as exc:
        _raise_for_speech_error(exc)


@router.websocket("/speech/stt/stream")
async def stream_transcribe_speech(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        start_message = await websocket.receive_json()
    except WebSocketDisconnect:
        return

    if start_message.get("type") != "start":
        await websocket.send_json({"type": "error", "code": "protocol_error", "detail": "expected a start frame"})
        await websocket.close()
        return

    backend = start_message.get("backend", "local")
    if backend != "local":
        await websocket.send_json(
            {
                "type": "error",
                "code": "unsupported_backend",
                "detail": "live streaming requires the local backend",
            }
        )
        await websocket.close()
        return

    language = start_message.get("language")
    match_commands = bool(start_message.get("match_commands", True))
    session = StreamSession()
    client = SpeechServiceClient()

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if (text := message.get("text")) is not None:
                try:
                    payload = json.loads(text)
                except ValueError:
                    logger.warning("speech stream: ignoring malformed text frame")
                    continue
                if payload.get("type") == "stop":
                    await _finish_stream(websocket, session, match_commands=match_commands)
                    break
                continue

            chunk_bytes = message.get("bytes")
            if not chunk_bytes:
                continue

            try:
                async with _live_stt_semaphore:
                    body = await client.transcribe(
                        chunk_bytes,
                        filename="chunk.webm",
                        content_type="audio/webm",
                        backend="local",
                        language=language,
                        initial_prompt=session.context_tail(),
                        vad_filter=True,
                        use_stream_model=True,
                        timeout=_STREAM_CHUNK_TIMEOUT_SECONDS,
                    )
            except SpeechServiceError as exc:
                await websocket.send_json({"type": "error", "detail": exc.detail})
                continue
            except httpx.HTTPError as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue
            except Exception:
                logger.exception("speech stream: unexpected error transcribing a chunk")
                await websocket.send_json(
                    {"type": "error", "detail": "internal error transcribing this chunk"}
                )
                continue

            try:
                full_text = session.append_chunk(body["transcript"])
                await websocket.send_json(
                    {"type": "partial", "chunk_text": body["transcript"], "full_text": full_text}
                )
            except Exception:
                logger.exception("speech stream: unexpected error handling a transcribed chunk")
                continue
    except WebSocketDisconnect:
        pass


async def _finish_stream(websocket: WebSocket, session: StreamSession, *, match_commands: bool = True) -> None:
    matched = None
    if match_commands:
        try:
            async with SessionLocal() as db_session:
                commands = await SpeechCommandRepository(db_session).list_active()
            command_defs = [
                SpeechCommandDef(
                    id=c.id,
                    phrase=c.phrase,
                    action=c.action,
                    language=c.language,
                    is_active=c.is_active,
                    created_at=c.created_at,
                )
                for c in commands
            ]
            matched = match_command(session.full_text, command_defs)
        except Exception:
            logger.exception("speech stream: failed to match commands while finishing")
    await websocket.send_json(
        {
            "type": "final",
            "text": session.full_text,
            "matched_command": SpeechCommandOut.model_validate(matched).model_dump(mode="json")
            if matched
            else None,
        }
    )
    await websocket.close()
