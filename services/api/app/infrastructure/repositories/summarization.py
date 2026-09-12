from __future__ import annotations

import datetime as dt

from ips_db import Document, DocumentSummary, DocumentSummaryPolish, DocumentTerm, SummarizationRun, Term
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import SummarizationRunStatus


class DocumentTermStatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_term_frequencies(self, document_id: int) -> dict[str, int]:
        result = await self._session.execute(
            select(Term.lemma, DocumentTerm.tf)
            .join(DocumentTerm, DocumentTerm.term_id == Term.id)
            .where(DocumentTerm.document_id == document_id)
        )
        return {lemma: tf for lemma, tf in result.all()}

    async def get_document_frequencies(
        self, collection_id: int, lemmas: set[str]
    ) -> dict[str, int]:
        if not lemmas:
            return {}
        result = await self._session.execute(
            select(Term.lemma, func.count(func.distinct(DocumentTerm.document_id)))
            .select_from(DocumentTerm)
            .join(Term, Term.id == DocumentTerm.term_id)
            .join(Document, Document.id == DocumentTerm.document_id)
            .where(Document.collection_id == collection_id, Term.lemma.in_(lemmas))
            .group_by(Term.lemma)
        )
        return {lemma: count for lemma, count in result.all()}


class SummarizationRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, collection_id: int, method: str) -> SummarizationRun:
        run = SummarizationRun(
            collection_id=collection_id, method=method, status=SummarizationRunStatus.PENDING.value
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, run_id: int) -> SummarizationRun | None:
        return await self._session.get(SummarizationRun, run_id)

    async def list_by_collection(self, collection_id: int) -> list[SummarizationRun]:
        result = await self._session.execute(
            select(SummarizationRun)
            .where(SummarizationRun.collection_id == collection_id)
            .order_by(SummarizationRun.id.desc())
        )
        return list(result.scalars().all())

    async def mark_running(self, run_id: int, *, documents_total: int) -> bool:
        result = await self._session.execute(
            update(SummarizationRun)
            .where(
                SummarizationRun.id == run_id,
                SummarizationRun.status == SummarizationRunStatus.PENDING.value,
            )
            .values(
                status=SummarizationRunStatus.RUNNING.value,
                documents_total=documents_total,
                started_at=dt.datetime.utcnow(),
            )
        )
        await self._session.commit()
        return result.rowcount > 0

    async def update_progress(self, run_id: int, *, documents_processed: int) -> None:
        run = await self._session.get(SummarizationRun, run_id)
        if run is None:
            return
        run.documents_processed = documents_processed
        await self._session.commit()

    async def mark_completed(self, run_id: int) -> None:
        run = await self._session.get(SummarizationRun, run_id)
        if run is None:
            return
        run.status = SummarizationRunStatus.COMPLETED.value
        run.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def mark_failed(self, run_id: int, *, error_message: str) -> None:
        run = await self._session.get(SummarizationRun, run_id)
        if run is None:
            return
        run.status = SummarizationRunStatus.FAILED.value
        run.error_message = error_message[:1000]
        run.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def mark_cancelled(self, run_id: int) -> None:
        run = await self._session.get(SummarizationRun, run_id)
        if run is None:
            return
        run.status = SummarizationRunStatus.CANCELLED.value
        run.finished_at = dt.datetime.utcnow()
        await self._session.commit()


class DocumentSummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        run_id: int | None,
        document_id: int,
        method: str,
        sentence_count: int,
        summary_text: str,
        summary_sentence_indices: list[int],
        total_sentences: int,
        total_chars: int,
        elapsed_ms: float,
    ) -> DocumentSummary:
        summary = DocumentSummary(
            run_id=run_id,
            document_id=document_id,
            method=method,
            sentence_count=sentence_count,
            summary_text=summary_text,
            summary_sentence_indices=summary_sentence_indices,
            total_sentences=total_sentences,
            total_chars=total_chars,
            elapsed_ms=elapsed_ms,
        )
        self._session.add(summary)
        await self._session.flush()
        return summary

    async def get(self, summary_id: int) -> DocumentSummary | None:
        return await self._session.get(DocumentSummary, summary_id)

    async def list_for_document(self, document_id: int) -> list[DocumentSummary]:
        result = await self._session.execute(
            select(DocumentSummary)
            .where(DocumentSummary.document_id == document_id)
            .order_by(DocumentSummary.id.desc())
        )
        return list(result.scalars().all())

    async def list_for_run(self, run_id: int) -> list[DocumentSummary]:
        result = await self._session.execute(
            select(DocumentSummary).where(DocumentSummary.run_id == run_id).order_by(DocumentSummary.id)
        )
        return list(result.scalars().all())


class DocumentSummaryPolishRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, document_summary_id: int, model: str, polished_text: str
    ) -> DocumentSummaryPolish:
        polish = DocumentSummaryPolish(
            document_summary_id=document_summary_id, model=model, polished_text=polished_text
        )
        self._session.add(polish)
        await self._session.flush()
        return polish

    async def list_for_summary(self, document_summary_id: int) -> list[DocumentSummaryPolish]:
        result = await self._session.execute(
            select(DocumentSummaryPolish)
            .where(DocumentSummaryPolish.document_summary_id == document_summary_id)
            .order_by(DocumentSummaryPolish.id.desc())
        )
        return list(result.scalars().all())
