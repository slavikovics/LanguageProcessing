from __future__ import annotations

import io
import os
import threading

_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")
_STREAM_MODEL_SIZE = os.environ.get("WHISPER_STREAM_MODEL_SIZE", "base")
# Stream path uses the faster "base" model so chunks don't fall behind real-time.
_CPU_THREADS = int(os.environ.get("WHISPER_CPU_THREADS", "2"))
# Caps thread pool so one transcription can't claim every core in the container.

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
    # Preloads models so a cold load doesn't blow the stream gateway's ~20s chunk timeout.
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
        # Stream chunks can be truncated by MediaRecorder restarts; treat as silence, not an error.
        if use_stream_model:
            return "", language_hint
        raise
