from __future__ import annotations

from ips_db import DocumentSummary, SummarizationRun
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import SummarizationRunStatus
from app.domain.summarization import SummarizationError, SummarizationRunSummary, summarize_run
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.summarization import (
    DocumentSummaryRepository,
    SummarizationRunRepository,
)

from .document_summarizer import DocumentSummarizationService
from .term_weights import compute_modified_term_weights

DEFAULT_SENTENCE_COUNT = 10
_ACTIVE_RUN_STATUSES = {SummarizationRunStatus.PENDING.value, SummarizationRunStatus.RUNNING.value}


class SummarizationTestRunService:

    def __init__(
        self, session: AsyncSession, *, summarizer: DocumentSummarizationService | None = None
    ) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._runs = SummarizationRunRepository(session)
        self._summaries = DocumentSummaryRepository(session)
        self._summarizer = summarizer or DocumentSummarizationService(session)

    async def start_run(self, collection_id: int, methods: list[str]) -> list[SummarizationRun]:
        documents = await self._documents.list_all_by_collection(collection_id)
        if not documents:
            raise SummarizationError("collection has no documents")
        runs = [await self._runs.create(collection_id=collection_id, method=method) for method in methods]
        await self._session.commit()
        return runs

    async def get_run(self, run_id: int) -> SummarizationRun | None:
        return await self._runs.get(run_id)

    async def list_runs_by_collection(self, collection_id: int) -> list[SummarizationRun]:
        return await self._runs.list_by_collection(collection_id)

    async def cancel_run(self, run_id: int) -> SummarizationRun:
        run = await self._runs.get(run_id)
        if run is None:
            raise SummarizationError(f"summarization run {run_id} not found")
        if run.status not in _ACTIVE_RUN_STATUSES:
            raise SummarizationError(f"summarization run {run_id} is already {run.status}")
        await self._runs.mark_cancelled(run_id)
        run.status = SummarizationRunStatus.CANCELLED.value
        return run

    async def run_job(self, run_id: int, *, sentence_count: int = DEFAULT_SENTENCE_COUNT) -> None:
        run = await self._runs.get(run_id)
        if run is None:
            return
        try:
            documents = await self._documents.list_all_by_collection(run.collection_id)
            started = await self._runs.mark_running(run_id, documents_total=len(documents))
            if not started:
                return

            for processed, document in enumerate(documents, start=1):
                current = await self._runs.get(run_id)
                if current is not None and current.status == SummarizationRunStatus.CANCELLED.value:
                    return
                try:
                    if run.method == "algorithmic":
                        term_weights = await compute_modified_term_weights(
                            self._session,
                            document_id=document.id,
                            collection_id=document.collection_id,
                        )
                        if not term_weights:
                            raise SummarizationError("document not indexed")
                    else:
                        term_weights = {}

                    outcome = await self._summarizer.run_method(
                        run.method, document.clean_text, term_weights, sentence_count
                    )
                    await self._summaries.create(
                        run_id=run_id,
                        document_id=document.id,
                        method=run.method,
                        sentence_count=sentence_count,
                        summary_text=outcome.summary_text,
                        summary_sentence_indices=[s.index for s in outcome.sentences],
                        total_sentences=outcome.total_sentences,
                        total_chars=outcome.document_chars,
                        elapsed_ms=outcome.elapsed_ms,
                    )
                except Exception:
                    pass
                await self._runs.update_progress(run_id, documents_processed=processed)

            await self._session.commit()
            final = await self._runs.get(run_id)
            if final is not None and final.status == SummarizationRunStatus.CANCELLED.value:
                return
            await self._runs.mark_completed(run_id)
        except Exception as exc:
            message = str(exc) or type(exc).__name__
            await self._runs.mark_failed(run_id, error_message=f"{type(exc).__name__}: {message}")

    async def get_run_results(self, run_id: int) -> list[DocumentSummary]:
        return await self._summaries.list_for_run(run_id)

    async def get_run_summary(self, run_id: int) -> SummarizationRunSummary:
        run = await self._runs.get(run_id)
        if run is None:
            raise SummarizationError(f"summarization run {run_id} not found")
        summaries = await self._summaries.list_for_run(run_id)
        return summarize_run(run_id=run_id, method=run.method, summaries=summaries)

    async def compare(self, collection_id: int, methods: list[str]) -> list[SummarizationRunSummary]:
        runs = await self._runs.list_by_collection(collection_id)
        summaries: list[SummarizationRunSummary] = []
        for method in methods:
            latest = next((run for run in runs if run.method == method and run.status == "completed"), None)
            if latest is None:
                continue
            summaries.append(await self.get_run_summary(latest.id))
        return summaries
