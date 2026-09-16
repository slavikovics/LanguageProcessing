from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from app.wav import build_wav_header

DEFAULT_VOICE = "en_US-amy-medium"
_VOICES_DIR = Path(os.environ.get("PIPER_VOICES_DIR", "/app/piper-voices"))

_voices: dict[str, object] = {}


def _get_voice(name: str):
    if name not in _voices:
        from piper import PiperVoice

        model_path = _VOICES_DIR / f"{name}.onnx"
        _voices[name] = PiperVoice.load(str(model_path))
    return _voices[name]


def synthesize_stream(text: str, *, voice: str | None = None, rate: float = 1.0) -> Iterator[bytes]:
    from piper import SynthesisConfig

    piper_voice = _get_voice(voice or DEFAULT_VOICE)
    syn_config = SynthesisConfig(length_scale=1.0 / rate if rate > 0 else 1.0)

    header_written = False
    for chunk in piper_voice.synthesize(text, syn_config=syn_config):
        if not header_written:
            yield build_wav_header(
                sample_rate=chunk.sample_rate,
                channels=chunk.sample_channels,
                bits_per_sample=chunk.sample_width * 8,
            )
            header_written = True
        yield chunk.audio_int16_bytes
