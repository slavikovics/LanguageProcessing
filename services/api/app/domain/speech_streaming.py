from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StreamSession:
    """Accumulates the sequence of independently-transcribed audio chunks
    from one /speech/stt/stream connection into a running transcript.

    Chunks are sequential, non-overlapping recordings (the frontend restarts
    MediaRecorder every ~3.5s rather than keeping one growing/rolling
    buffer — see the plan), so there's no LocalAgreement-style prefix
    diffing to do: each chunk's text is simply appended once it comes back.
    """

    words: list[str] = field(default_factory=list)

    def append_chunk(self, chunk_transcript: str) -> str:
        """Normalizes and appends one chunk's transcript; returns the full
        accumulated text so far. Empty/whitespace-only chunk transcripts
        (silence, a clipped fragment vad_filter dropped entirely) are
        skipped rather than leaving stray joins in the accumulated text."""
        cleaned = " ".join(chunk_transcript.split())
        if cleaned:
            self.words.append(cleaned)
        return self.full_text

    @property
    def full_text(self) -> str:
        return " ".join(self.words)

    def context_tail(self, max_chars: int = 200) -> str | None:
        """Tail of the accumulated text passed as the next chunk's
        initial_prompt, so faster-whisper has continuity across chunk
        boundaries instead of transcribing each chunk cold."""
        text = self.full_text
        if not text:
            return None
        return text[-max_chars:]
