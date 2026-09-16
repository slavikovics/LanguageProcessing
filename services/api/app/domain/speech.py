from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass


class SpeechError(ValueError):
    pass


@dataclass(frozen=True)
class TranscriptionOutcome:
    transcript: str
    detected_language: str | None
    backend_used: str
    elapsed_ms: float


@dataclass(frozen=True)
class SpeechCommandDef:
    id: int
    phrase: str
    action: str
    language: str
    is_active: bool
    created_at: dt.datetime


_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Lowercase, punctuation -> space (not deleted, so "stop-reading" still
    matches "stop reading" instead of colliding into "stopreading"), then
    collapse repeated whitespace."""
    despaced = _PUNCT_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", despaced).lower().strip()


def match_command(
    transcript: str, commands: list[SpeechCommandDef]
) -> SpeechCommandDef | None:
    """First active command whose phrase appears (normalized, case/punct
    insensitive) in the transcript — the LR9 'automatic reaction' trigger."""
    normalized = _normalize(transcript)
    if not normalized:
        return None
    for command in commands:
        if not command.is_active:
            continue
        if _normalize(command.phrase) in normalized:
            return command
    return None
