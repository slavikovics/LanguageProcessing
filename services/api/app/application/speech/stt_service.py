from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.speech import SpeechCommandDef, TranscriptionOutcome, match_command
from app.infrastructure.repositories.speech import SpeechCommandRepository
from app.infrastructure.speech_client import SpeechServiceClient


class SpeechRecognitionService:
    def __init__(self, session: AsyncSession, *, client: SpeechServiceClient | None = None) -> None:
        self._commands = SpeechCommandRepository(session)
        self._client = client or SpeechServiceClient()

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        content_type: str,
        backend: str,
        language: str | None,
    ) -> tuple[TranscriptionOutcome, SpeechCommandDef | None]:
        body = await self._client.transcribe(
            audio_bytes,
            filename=filename,
            content_type=content_type,
            backend=backend,
            language=language,
        )
        outcome = TranscriptionOutcome(
            transcript=body["transcript"],
            detected_language=body.get("detected_language"),
            backend_used=body["backend_used"],
            elapsed_ms=body["elapsed_ms"],
        )

        active_commands = await self._commands.list_active()
        command_defs = [
            SpeechCommandDef(
                id=c.id,
                phrase=c.phrase,
                action=c.action,
                language=c.language,
                is_active=c.is_active,
                created_at=c.created_at,
            )
            for c in active_commands
        ]
        matched = match_command(outcome.transcript, command_defs)
        return outcome, matched
