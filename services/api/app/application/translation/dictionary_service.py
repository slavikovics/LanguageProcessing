from __future__ import annotations

from ips_db import TranslationDictionaryEntry
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.translation import TranslationError
from app.infrastructure.repositories.translation import TranslationDictionaryRepository

_DUPLICATE_ENTRY_MESSAGE = (
    "a dictionary entry for this word (same language pair, lemma and part of speech) already exists"
)


class TranslationDictionaryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entries = TranslationDictionaryRepository(session)

    async def list_entries(self, **kwargs) -> tuple[list[TranslationDictionaryEntry], int]:
        items = await self._entries.list_entries(**kwargs)
        total = await self._entries.count_entries(
            **{k: v for k, v in kwargs.items() if k in ("source_lang", "target_lang", "search")}
        )
        return items, total

    async def create(self, **kwargs) -> TranslationDictionaryEntry:
        try:
            entry = await self._entries.create(**kwargs)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise TranslationError(_DUPLICATE_ENTRY_MESSAGE) from exc
        return entry

    async def update(self, entry_id: int, **kwargs) -> TranslationDictionaryEntry:
        try:
            entry = await self._entries.update(entry_id, **kwargs)
            if entry is None:
                raise TranslationError(f"dictionary entry {entry_id} not found")
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise TranslationError(_DUPLICATE_ENTRY_MESSAGE) from exc
        return entry

    async def delete(self, entry_id: int) -> None:
        deleted = await self._entries.delete(entry_id)
        if not deleted:
            raise TranslationError(f"dictionary entry {entry_id} not found")
        await self._session.commit()
