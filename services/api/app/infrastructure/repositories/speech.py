from __future__ import annotations

from ips_db import SpeechCommand
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class SpeechCommandRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[SpeechCommand]:
        result = await self._session.execute(select(SpeechCommand).order_by(SpeechCommand.id))
        return list(result.scalars().all())

    async def list_active(self, language: str | None = None) -> list[SpeechCommand]:
        query = select(SpeechCommand).where(SpeechCommand.is_active.is_(True))
        if language:
            query = query.where(SpeechCommand.language == language)
        result = await self._session.execute(query.order_by(SpeechCommand.id))
        return list(result.scalars().all())

    async def get(self, command_id: int) -> SpeechCommand | None:
        return await self._session.get(SpeechCommand, command_id)

    async def create(
        self, *, phrase: str, action: str, language: str = "en", is_active: bool = True
    ) -> SpeechCommand:
        command = SpeechCommand(
            phrase=phrase.strip(), action=action.strip(), language=language, is_active=is_active
        )
        self._session.add(command)
        await self._session.flush()
        return command

    async def update(
        self,
        command_id: int,
        *,
        phrase: str | None = None,
        action: str | None = None,
        language: str | None = None,
        is_active: bool | None = None,
    ) -> SpeechCommand | None:
        command = await self._session.get(SpeechCommand, command_id)
        if command is None:
            return None
        if phrase is not None:
            command.phrase = phrase.strip()
        if action is not None:
            command.action = action.strip()
        if language is not None:
            command.language = language
        if is_active is not None:
            command.is_active = is_active
        await self._session.flush()
        return command

    async def delete(self, command_id: int) -> bool:
        result = await self._session.execute(
            delete(SpeechCommand).where(SpeechCommand.id == command_id)
        )
        return result.rowcount > 0
