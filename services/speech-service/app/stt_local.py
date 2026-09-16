from __future__ import annotations

import io
import os
import threading

_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")
_STREAM_MODEL_SIZE = os.environ.get("WHISPER_STREAM_MODEL_SIZE", "base")
"""Live/streaming chunks (services/api's /speech/stt/stream gateway) use a
smaller, faster model than the default batch /stt endpoint: benchmarked
against this container, "small" takes ~1.4x real-time to transcribe a clip
(chunks would fall progressively further behind during continuous speech),
while "base" comfortably runs at ~0.3-0.5x real-time — the accuracy/latency
trade-off is worth it specifically for the live path, where a later full-
accuracy pass isn't part of the design. The batch endpoint keeps "small" as
its default, unchanged."""
_CPU_THREADS = int(os.environ.get("WHISPER_CPU_THREADS", "2"))
"""Caps ctranslate2's intra-op thread pool so one transcription can't claim
every core in the container — left unset, faster-whisper defaults to using
all visible CPUs, which starves the rest of the container's cpus= budget
(see docker-compose.yml) and can push it into throttling/OOM under load."""

_model = None
_stream_model = None
_model_lock = threading.Lock()
_stream_model_lock = threading.Lock()


def _load(model_size: str):
    from faster_whisper import WhisperModel

    return WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        cpu_threads=_CPU_THREADS,
        download_root=os.environ.get("SPEECH_MODELS_DIR"),
    )


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = _load(_MODEL_SIZE)
    return _model


def _get_stream_model():
    global _stream_model
    if _stream_model is None:
        with _stream_model_lock:
            if _stream_model is None:
                _stream_model = _load(_STREAM_MODEL_SIZE)
    return _stream_model


def warmup() -> None:
    """Eagerly loads both Whisper models (called once from main.py's startup
    hook, off the event loop thread) so the first real request doesn't pay
    the model-load cost itself. This matters most for the stream model: the
    live-transcription gateway (services/api's /speech/stt/stream) gives
    each chunk a fixed ~20s ceiling before reporting an error, and a cold
    faster-whisper load can easily take longer than that — which used to
    surface to the user as a spurious "connection lost" on the very first
    utterance spoken after this container (re)started, since it looked
    identical to a genuinely failed chunk from the gateway's side."""
    _get_stream_model()
    _get_model()


def transcribe(
    audio_bytes: bytes,
    *,
    language_hint: str | None = None,
    initial_prompt: str | None = None,
    vad_filter: bool = False,
    use_stream_model: bool = False,
) -> tuple[str, str | None]:
    model = _get_stream_model() if use_stream_model else _get_model()
    try:
        segments, info = model.transcribe(
            io.BytesIO(audio_bytes),
            language=language_hint,
            beam_size=5,
            initial_prompt=initial_prompt,
            vad_filter=vad_filter,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text, info.language
    except Exception:
        # The live-streaming path (/speech/stt/stream) restarts MediaRecorder
        # every ~3.5s to get independently-decodable chunks, but a chunk that
        # gets cut short by a manual stop (or is otherwise too brief for the
        # browser's encoder to finalize a valid container) can come back as
        # an empty/truncated file that av/faster-whisper can't open at all
        # (av.error.FFmpegError, e.g. "End of file") — surfacing that as a
        # 500 for every such chunk would make ordinary short utterances look
        # broken. Treat it the same as vad_filter already treats silence: no
        # speech found in this chunk, not a request failure. The batch /stt
        # endpoint (use_stream_model=False) still raises: a genuinely
        # undecodable *complete* recording is worth surfacing to the user.
        if use_stream_model:
            return "", language_hint
        raise
