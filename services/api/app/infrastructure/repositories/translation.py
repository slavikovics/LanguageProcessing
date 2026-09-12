from __future__ import annotations

from ips_db import TranslationDictionaryEntry, TranslationRun, TranslationRunWord
from ips_db.models.translation import ANY_POS
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class TranslationDictionaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def as_lookup(self, *, source_lang: str, target_lang: str) -> dict[str, str]:
        """Builds the `{"lemma|POS": target}` map nlp_core.translation.translate()
        expects. Every entry also seeds a `"lemma|*"` fallback (first entry
        for that lemma wins, in id order) — even though every entry now
        carries a real POS tag rather than the `ANY_POS` sentinel, a word
        used with a different POS than the dictionary happened to tag it
        with should still resolve instead of going untranslated."""
        result = await self._session.execute(
            select(
                TranslationDictionaryEntry.source_lemma,
                TranslationDictionaryEntry.pos,
                TranslationDictionaryEntry.target_text,
            )
            .where(
                TranslationDictionaryEntry.source_lang == source_lang,
                TranslationDictionaryEntry.target_lang == target_lang,
            )
            .order_by(TranslationDictionaryEntry.id)
        )
        lookup: dict[str, str] = {}
        for lemma, pos, target in result.all():
            lemma = lemma.lower()
            lookup[f"{lemma}|{pos}"] = target
            lookup.setdefault(f"{lemma}|{ANY_POS}", target)
        return lookup

    async def list_entries(
        self,
        *,
        source_lang: str | None = None,
        target_lang: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TranslationDictionaryEntry]:
        stmt = select(TranslationDictionaryEntry)
        if source_lang:
            stmt = stmt.where(TranslationDictionaryEntry.source_lang == source_lang)
        if target_lang:
            stmt = stmt.where(TranslationDictionaryEntry.target_lang == target_lang)
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                func.lower(TranslationDictionaryEntry.source_lemma).like(like)
                | func.lower(TranslationDictionaryEntry.target_text).like(like)
            )
        stmt = stmt.order_by(TranslationDictionaryEntry.source_lemma).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_entries(
        self,
        *,
        source_lang: str | None = None,
        target_lang: str | None = None,
        search: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(TranslationDictionaryEntry)
        if source_lang:
            stmt = stmt.where(TranslationDictionaryEntry.source_lang == source_lang)
        if target_lang:
            stmt = stmt.where(TranslationDictionaryEntry.target_lang == target_lang)
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                func.lower(TranslationDictionaryEntry.source_lemma).like(like)
                | func.lower(TranslationDictionaryEntry.target_text).like(like)
            )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get(self, entry_id: int) -> TranslationDictionaryEntry | None:
        return await self._session.get(TranslationDictionaryEntry, entry_id)

    async def create(
        self,
        *,
        source_lang: str,
        target_lang: str,
        source_lemma: str,
        pos: str | None,
        target_text: str,
        notes: str | None,
    ) -> TranslationDictionaryEntry:
        entry = TranslationDictionaryEntry(
            source_lang=source_lang,
            target_lang=target_lang,
            source_lemma=source_lemma.strip().lower(),
            pos=pos or ANY_POS,
            target_text=target_text.strip(),
            notes=notes,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def update(
        self,
        entry_id: int,
        *,
        target_text: str | None = None,
        pos: str | None = ...,
        notes: str | None = ...,
    ) -> TranslationDictionaryEntry | None:
        entry = await self._session.get(TranslationDictionaryEntry, entry_id)
        if entry is None:
            return None
        if target_text is not None:
            entry.target_text = target_text.strip()
        if pos is not ...:
            entry.pos = pos or ANY_POS
        if notes is not ...:
            entry.notes = notes
        await self._session.flush()
        return entry

    async def delete(self, entry_id: int) -> bool:
        result = await self._session.execute(
            delete(TranslationDictionaryEntry).where(TranslationDictionaryEntry.id == entry_id)
        )
        return result.rowcount > 0


class TranslationRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        document_id: int | None,
        collection_id: int | None,
        source_lang: str,
        target_lang: str,
        source_text: str,
        translated_text: str,
        word_count: int,
        translated_word_count: int,
        elapsed_ms: float,
    ) -> TranslationRun:
        run = TranslationRun(
            document_id=document_id,
            collection_id=collection_id,
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=source_text,
            translated_text=translated_text,
            word_count=word_count,
            translated_word_count=translated_word_count,
            elapsed_ms=elapsed_ms,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, run_id: int) -> TranslationRun | None:
        return await self._session.get(TranslationRun, run_id)

    async def list_recent(self, *, limit: int = 20) -> list[TranslationRun]:
        result = await self._session.execute(
            select(TranslationRun).order_by(TranslationRun.id.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_for_collection(self, collection_id: int) -> TranslationRun | None:
        result = await self._session.execute(
            select(TranslationRun)
            .where(TranslationRun.collection_id == collection_id)
            .order_by(TranslationRun.id.desc())
            .limit(1)
        )
        return result.scalars().first()


class TranslationRunWordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, run_id: int, words: list[dict]) -> None:
        self._session.add_all(
            [
                TranslationRunWord(
                    run_id=run_id,
                    rank=index,
                    lemma=word["lemma"],
                    surface=word["surface"],
                    pos=word["pos"],
                    frequency=word["frequency"],
                    translation=word["translation"],
                )
                for index, word in enumerate(words, start=1)
            ]
        )
        await self._session.flush()

    async def list_for_run(self, run_id: int) -> list[TranslationRunWord]:
        result = await self._session.execute(
            select(TranslationRunWord)
            .where(TranslationRunWord.run_id == run_id)
            .order_by(TranslationRunWord.rank)
        )
        return list(result.scalars().all())
