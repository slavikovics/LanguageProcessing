from __future__ import annotations

import datetime as dt

from ips_db import TranslationDictionaryEntry, TranslationRun, TranslationRunWord, TranslationTestRun
from ips_db.models.translation import ANY_POS
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TranslationTestRunStatus


class TranslationDictionaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def as_lookup(self, *, source_lang: str, target_lang: str) -> dict[str, str]:
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
        method: str = "direct",
        test_run_id: int | None = None,
        translated_text_word_count: int = 0,
        diff_segments: list | None = None,
    ) -> TranslationRun:
        run = TranslationRun(
            document_id=document_id,
            collection_id=collection_id,
            test_run_id=test_run_id,
            source_lang=source_lang,
            target_lang=target_lang,
            method=method,
            source_text=source_text,
            translated_text=translated_text,
            word_count=word_count,
            translated_word_count=translated_word_count,
            translated_text_word_count=translated_text_word_count,
            elapsed_ms=elapsed_ms,
            diff_segments=diff_segments,
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

    async def get_latest_for_collection(
        self, collection_id: int, *, method: str | None = None
    ) -> TranslationRun | None:
        stmt = select(TranslationRun).where(TranslationRun.collection_id == collection_id)
        if method is not None:
            stmt = stmt.where(TranslationRun.method == method)
        result = await self._session.execute(stmt.order_by(TranslationRun.id.desc()).limit(1))
        return result.scalars().first()

    async def list_for_test_run(self, test_run_id: int) -> list[TranslationRun]:
        result = await self._session.execute(
            select(TranslationRun)
            .where(TranslationRun.test_run_id == test_run_id)
            .order_by(TranslationRun.id)
        )
        return list(result.scalars().all())


class TranslationTestRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, collection_id: int, source_lang: str, target_lang: str, method: str = "direct"
    ) -> TranslationTestRun:
        run = TranslationTestRun(
            collection_id=collection_id,
            source_lang=source_lang,
            target_lang=target_lang,
            method=method,
            status=TranslationTestRunStatus.PENDING.value,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, run_id: int) -> TranslationTestRun | None:
        return await self._session.get(TranslationTestRun, run_id)

    async def list_by_collection(
        self, collection_id: int, *, method: str | None = None
    ) -> list[TranslationTestRun]:
        stmt = select(TranslationTestRun).where(TranslationTestRun.collection_id == collection_id)
        if method is not None:
            stmt = stmt.where(TranslationTestRun.method == method)
        result = await self._session.execute(stmt.order_by(TranslationTestRun.id.desc()))
        return list(result.scalars().all())

    async def mark_running(self, run_id: int, *, documents_total: int) -> bool:
        result = await self._session.execute(
            update(TranslationTestRun)
            .where(
                TranslationTestRun.id == run_id,
                TranslationTestRun.status == TranslationTestRunStatus.PENDING.value,
            )
            .values(
                status=TranslationTestRunStatus.RUNNING.value,
                documents_total=documents_total,
                started_at=dt.datetime.utcnow(),
            )
        )
        await self._session.commit()
        return result.rowcount > 0

    async def update_progress(self, run_id: int, *, documents_processed: int) -> None:
        run = await self._session.get(TranslationTestRun, run_id)
        if run is None:
            return
        run.documents_processed = documents_processed
        await self._session.commit()

    async def mark_completed(self, run_id: int, *, error_message: str | None = None) -> None:
        run = await self._session.get(TranslationTestRun, run_id)
        if run is None:
            return
        run.status = TranslationTestRunStatus.COMPLETED.value
        run.finished_at = dt.datetime.utcnow()
        if error_message is not None:
            run.error_message = error_message[:1000]
        await self._session.commit()

    async def mark_failed(self, run_id: int, *, error_message: str) -> None:
        run = await self._session.get(TranslationTestRun, run_id)
        if run is None:
            return
        run.status = TranslationTestRunStatus.FAILED.value
        run.error_message = error_message[:1000]
        run.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def mark_cancelled(self, run_id: int) -> None:
        run = await self._session.get(TranslationTestRun, run_id)
        if run is None:
            return
        run.status = TranslationTestRunStatus.CANCELLED.value
        run.finished_at = dt.datetime.utcnow()
        await self._session.commit()


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
