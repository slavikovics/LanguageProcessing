from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StreamSession:
    words: list[str] = field(default_factory=list)

    def append_chunk(self, chunk_transcript: str) -> str:
        cleaned = " ".join(chunk_transcript.split())
        if cleaned:
            self.words.append(cleaned)
        return self.full_text

    @property
    def full_text(self) -> str:
        return " ".join(self.words)

    def context_tail(self, max_chars: int = 200) -> str | None:
        text = self.full_text
        if not text:
            return None
        return text[-max_chars:]
