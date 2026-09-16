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

MAX_AUDIO_UPLOAD_BYTES = 25 * 1024 * 1024
"""Matches speech-service's MAX_AUDIO_UPLOAD_BYTES (app/routes.py) so an
oversized upload is rejected here instead of being proxied across the
network only to be rejected on the other side."""

_STREAM_CHUNK_TIMEOUT_SECONDS = 20.0
"""Each /speech/stt/stream chunk is a few seconds of audio transcribed by
speech-service's smaller "stream" model — this should return in well under
a second normally; 20s is a generous ceiling for one slow chunk, not the
150s worst-case budget the batch /speech/stt route needs."""

_live_stt_semaphore = asyncio.Semaphore(get_settings().speech_stream_max_concurrency)
"""Bounds how many chunks across every open ambient-listening/dictation
session this api process will have in flight against speech-service at
once, so concurrent live sessions can't collectively exceed that
container's cpus= budget (docker-compose.yml)."""


def _raise_for_speech_error(exc: SpeechError) -> None:
    status = 404 if "not found" in str(exc) else 422
    raise HTTPException(status_code=status, detail=str(exc)) from exc


async def _read_capped(upload: UploadFile, max_bytes: int) -> bytes:
    """Reads the upload in chunks so an oversized file is rejected without
    ever buffering more than max_bytes + one chunk into memory."""
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
    """Live-dictation gateway: the browser restarts MediaRecorder every
    ~3.5s and sends each independent chunk as a binary frame; each chunk is
    forwarded to speech-service's /stt (smaller "stream" model,
    vad_filter=True) and the running transcript is relayed back as JSON,
    until a {"type":"stop"} frame triggers a final command-match pass. Local
    backend only — it's the only backend the app supports at all now, but
    this is also the one path that structurally couldn't use a cloud
    backend anyway (a network round-trip every ~3.5s isn't practical)."""
    await websocket.accept()

    try:
        start_message = await websocket.receive_json()
    except WebSocketDisconnect:
        # A client that connects and disconnects before ever sending its
        # start frame (tab closed/navigated away mid-handshake) is a normal
        # occurrence, not a server error — receive_json() otherwise raises
        # this uncaught, which surfaces as a logged ASGI exception for
        # nothing more than an ordinary early disconnect.
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
    # Settings' STT "check" widget just previews recognition accuracy — it
    # has no onCommand consumer at all, so there's nothing useful to do with
    # a match there, only the cost of the extra DB query and (if the spoken
    # test text happens to contain a trigger phrase) a misleading "Команда
    # распознана" notice for a command that isn't actually being acted on.
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
                    # A malformed text frame previously propagated out of
                    # this loop uncaught, which tears the WebSocket down
                    # ungracefully (see the broad except Exception blocks
                    # below for the same rationale) — just ignore it.
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
                # A single slow/reset chunk (speech-service momentarily
                # overloaded, a dropped connection) shouldn't kill the whole
                # ambient/dictation session — report it and keep listening
                # for the next chunk, same as a SpeechServiceError above.
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue
            except Exception:
                # Anything else here (e.g. a malformed speech-service
                # response) previously propagated out of this loop
                # uncaught, which crashes the WebSocket ungracefully — the
                # browser just sees the connection drop with no "final"
                # ever having arrived, reported to the user as the
                # connection having died rather than one bad chunk. Log it
                # and keep the session alive for the next chunk instead.
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
            # A DB hiccup here shouldn't cost the user their transcript — this
            # previously ran with no try/except, so an error propagated out of
            # this coroutine uncaught and crashed the WebSocket before "final"
            # was ever sent, which the browser reports as the connection having
            # been lost rather than "no command matched". Deliver the
            # transcript anyway, just without a matched command.
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
