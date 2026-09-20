from __future__ import annotations

import logging

from ips_db import TranslationRun, TranslationTestRun
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TranslationTestRunStatus
from app.domain.translation import (
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    TranslationError,
    TranslationRunSummary,
    summarize_translation_run,
)
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.translation import (
    TranslationDictionaryRepository,
    TranslationRunRepository,
    TranslationTestRunRepository,
)

from .translation_service import TranslationService

logger = logging.getLogger(__name__)

_ACTIVE_RUN_STATUSES = {TranslationTestRunStatus.PENDING.value, TranslationTestRunStatus.RUNNING.value}


class TranslationTestRunService:

    def __init__(
        self, session: AsyncSession, *, translation_service: TranslationService | None = None
    ) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._dictionary = TranslationDictionaryRepository(session)
        self._test_runs = TranslationTestRunRepository(session)
        self._runs = TranslationRunRepository(session)
        self._translator = translation_service or TranslationService(session)

    async def start_run(
        self,
        collection_id: int,
        *,
        source_lang: str = DEFAULT_SOURCE_LANGUAGE,
        target_lang: str = DEFAULT_TARGET_LANGUAGE,
        method: str = "direct",
    ) -> TranslationTestRun:
        documents = await self._documents.list_all_by_collection(collection_id, language=source_lang)
        if not documents:
            raise TranslationError(f"collection has no documents in language '{source_lang}'")
        run = await self._test_runs.create(
            collection_id=collection_id, source_lang=source_lang, target_lang=target_lang, method=method
        )
        await self._session.commit()
        return run

    async def get_run(self, run_id: int) -> TranslationTestRun | None:
        return await self._test_runs.get(run_id)

    async def list_runs_by_collection(
        self, collection_id: int, *, method: str | None = None
    ) -> list[TranslationTestRun]:
        return await self._test_runs.list_by_collection(collection_id, method=method)

    async def cancel_run(self, run_id: int) -> TranslationTestRun:
        run = await self._test_runs.get(run_id)
        if run is None:
            raise TranslationError(f"translation test run {run_id} not found")
        if run.status not in _ACTIVE_RUN_STATUSES:
            raise TranslationError(f"translation test run {run_id} is already {run.status}")
        await self._test_runs.mark_cancelled(run_id)
        run.status = TranslationTestRunStatus.CANCELLED.value
        return run

    async def run_job(self, run_id: int) -> None:
        run = await self._test_runs.get(run_id)
        if run is None:
            return
        try:
            documents = await self._documents.list_all_by_collection(
                run.collection_id, language=run.source_lang
            )
            started = await self._test_runs.mark_running(run_id, documents_total=len(documents))
            if not started:
                return

            lookup = await self._dictionary.as_lookup(
                source_lang=run.source_lang, target_lang=run.target_lang
            )

            source_lang, target_lang, method = run.source_lang, run.target_lang, run.method
            document_specs = [(doc.id, doc.collection_id) for doc in documents]

            failures: list[str] = []
            for processed, (document_id, document_collection_id) in enumerate(document_specs, start=1):
                current = await self._test_runs.get(run_id)
                if current is not None and current.status == TranslationTestRunStatus.CANCELLED.value:
                    return
                try:
                    await self._translator.translate(
                        document_id=document_id,
                        text=None,
                        collection_id=document_collection_id,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        method=method,
                        test_run_id=run_id,
                        lookup_override=lookup,
                    )
                except Exception as exc:
                    await self._session.rollback()
                    logger.exception(
                        "translation test run %s: document %s failed (method=%s)",
                        run_id, document_id, method,
                    )
                    failures.append(f"document {document_id}: {type(exc).__name__}: {exc}")
                await self._test_runs.update_progress(run_id, documents_processed=processed)

            final = await self._test_runs.get(run_id)
            if final is not None and final.status == TranslationTestRunStatus.CANCELLED.value:
                return

            if failures and len(failures) == len(documents):
                await self._test_runs.mark_failed(
                    run_id,
                    error_message=f"all {len(documents)} documents failed to translate; last error: {failures[-1]}",
                )
                return

            error_message = (
                f"{len(failures)} of {len(documents)} documents failed to translate; "
                f"last error: {failures[-1]}"
                if failures
                else None
            )
            await self._test_runs.mark_completed(run_id, error_message=error_message)
        except Exception as exc:
            message = str(exc) or type(exc).__name__
            await self._test_runs.mark_failed(run_id, error_message=f"{type(exc).__name__}: {message}")

    async def get_run_results(self, run_id: int) -> list[TranslationRun]:
        return await self._runs.list_for_test_run(run_id)

    async def get_run_summary(self, run_id: int) -> TranslationRunSummary:
        run = await self._test_runs.get(run_id)
        if run is None:
            raise TranslationError(f"translation test run {run_id} not found")
        runs = await self._runs.list_for_test_run(run_id)
        return summarize_translation_run(
            run_id=run_id,
            source_lang=run.source_lang,
            target_lang=run.target_lang,
            method=run.method,
            runs=runs,
        )
