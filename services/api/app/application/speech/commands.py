from __future__ import annotations

from ips_db import SpeechCommand
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.speech import SpeechError
from app.infrastructure.repositories.speech import SpeechCommandRepository


class SpeechCommandService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._commands = SpeechCommandRepository(session)

    async def list_commands(self) -> list[SpeechCommand]:
        return await self._commands.list_all()

    async def create_command(
        self, *, phrase: str, action: str, language: str = "en", is_active: bool = True
    ) -> SpeechCommand:
        command = await self._commands.create(
            phrase=phrase, action=action, language=language, is_active=is_active
        )
        await self._session.commit()
        return command

    async def update_command(self, command_id: int, **kwargs) -> SpeechCommand:
        command = await self._commands.update(command_id, **kwargs)
        if command is None:
            raise SpeechError(f"speech command {command_id} not found")
        await self._session.commit()
        return command

    async def delete_command(self, command_id: int) -> None:
        deleted = await self._commands.delete(command_id)
        if not deleted:
            raise SpeechError(f"speech command {command_id} not found")
        await self._session.commit()
