from __future__ import annotations

from ips_db import Document, LangIdResult, LangIdRun
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lang_id import IdentificationOutcome, LangIdError, LangIdRunSummary, summarize_results
from app.infrastructure.lang_id_client import LangIdServiceClient
from app.infrastructure.repositories.chunk_embeddings import ChunkEmbeddingRepository
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.lang_id import (
    LangIdProfileRepository,
    LangIdResultRepository,
    LangIdRunMetricRepository,
    LangIdRunRepository,
)
from app.infrastructure.repositories.search_models import SearchModelRepository

from .identification import LangIdIdentificationService
from .stored_embeddings import stored_vectors_for


class LangIdTestRunService:
    """Runs one method's classifier over a collection's whole test split and
    scores the result — the batch counterpart to LangIdIdentificationService's
    one-off classification."""

    def __init__(self, session: AsyncSession, *, lang_id_client: LangIdServiceClient | None = None) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._profiles = LangIdProfileRepository(session)
        self._runs = LangIdRunRepository(session)
        self._results = LangIdResultRepository(session)
        self._run_metrics = LangIdRunMetricRepository(session)
        self._chunk_embeddings = ChunkEmbeddingRepository(session)
        self._search_models = SearchModelRepository(session)
        self._lang_id = lang_id_client or LangIdServiceClient()
        self._identification = LangIdIdentificationService(session, lang_id_client=self._lang_id)

    async def start_run(self, collection_id: int, methods: list[str]) -> list[LangIdRun]:
        documents = await self._documents.list_test_documents(collection_id)
        if not documents:
            raise LangIdError("collection has no labeled test documents")
        runs = [await self._runs.create(collection_id=collection_id, method=method) for method in methods]
        await self._session.commit()
        return runs

    async def get_run(self, run_id: int) -> LangIdRun | None:
        return await self._runs.get(run_id)

    async def list_runs_by_collection(self, collection_id: int) -> list[LangIdRun]:
        return await self._runs.list_by_collection(collection_id)

    async def _identify_for_run(
        self, method: str, documents: list[Document]
    ) -> dict[int, IdentificationOutcome]:
        """The lexical methods classify one document at a time (cheap,
        in-process math in lang-id-service); neural instead batches every
        document's already-stored embedding into one request."""
        if method != "neural":
            outcomes: dict[int, IdentificationOutcome] = {}
            for document in documents:
                found = await self._identification.identify_text(document.clean_text, [method])
                if found:
                    outcomes[document.id] = found[0]
            return outcomes

        profile = await self._profiles.get("neural", None)
        if profile is None:
            return {}
        data = profile.profile_data
        vectors = await stored_vectors_for(
            documents, chunk_embeddings=self._chunk_embeddings, search_models=self._search_models
        )
        outcomes = {}
        for document, vector in zip(documents, vectors):
            result = await self._lang_id.identify_neural(
                data["weights"], data["bias"], data["classes"], vector
            )
            outcomes[document.id] = IdentificationOutcome(
                method="neural",
                predicted_language=result["predicted_language"],
                distances=result["distances"],
                elapsed_ms=result["elapsed_ms"],
            )
        return outcomes

    async def run_job(self, run_id: int) -> None:
        run = await self._runs.get(run_id)
        if run is None:
            return
        try:
            documents = await self._documents.list_test_documents(run.collection_id)
            started = await self._runs.mark_running(run_id, documents_total=len(documents))
            if not started:
                return

            await self._results.clear_for_run(run_id)
            outcomes_by_document_id = await self._identify_for_run(run.method, documents)

            rows: list[dict[str, object]] = []
            for processed, document in enumerate(documents, start=1):
                outcome = outcomes_by_document_id.get(document.id)
                if outcome is not None:
                    rows.append(
                        {
                            "run_id": run_id,
                            "document_id": document.id,
                            "predicted_language": outcome.predicted_language,
                            "distances": outcome.distances,
                            "elapsed_ms": outcome.elapsed_ms,
                            "is_correct": outcome.predicted_language == document.confirmed_language,
                        }
                    )
                await self._runs.update_progress(run_id, documents_processed=processed)

            await self._results.bulk_write(rows)
            await self._session.commit()
            await self._runs.mark_completed(run_id)
        except Exception as exc:  # pragma: no cover - top-level safety net
            message = str(exc) or type(exc).__name__
            await self._runs.mark_failed(run_id, error_message=f"{type(exc).__name__}: {message}")

    async def get_run_results(self, run_id: int) -> list[LangIdResult]:
        return await self._results.list_for_run(run_id)

    async def get_run_summary(self, run_id: int) -> LangIdRunSummary:
        run = await self._runs.get(run_id)
        if run is None:
            raise LangIdError(f"lang-id run {run_id} not found")
        results = await self._results.list_for_run(run_id)
        documents = await self._documents.list_by_ids([result.document_id for result in results])
        actual_language = {document.id: document.confirmed_language for document in documents}
        pairs = [
            (actual_language.get(result.document_id) or "", result.predicted_language) for result in results
        ]
        elapsed_values = [result.elapsed_ms for result in results]
        summary = summarize_results(
            run_id=run_id, method=run.method, actual_predicted_pairs=pairs, elapsed_ms_values=elapsed_values
        )

        await self._run_metrics.replace_for_run(
            run_id,
            {
                "accuracy": summary.accuracy,
                "precision": summary.precision,
                "recall": summary.recall,
                "f1": summary.f1,
                "mean_elapsed_ms": summary.mean_elapsed_ms,
            },
        )
        await self._session.commit()
        return summary

    async def compare(self, collection_id: int, methods: list[str]) -> list[LangIdRunSummary]:
        """Latest completed run per requested method for this collection."""
        runs = await self._runs.list_by_collection(collection_id)
        summaries: list[LangIdRunSummary] = []
        for method in methods:
            latest = next((run for run in runs if run.method == method and run.status == "completed"), None)
            if latest is None:
                continue
            summaries.append(await self.get_run_summary(latest.id))
        return summaries

    async def rerun_and_compare(self, collection_id: int, methods: list[str]) -> list[LangIdRunSummary]:
        """Starts fresh runs for every requested method and waits for them
        to finish, so numbers reflect the current profiles/classifier rather
        than a possibly stale run."""
        runs = await self.start_run(collection_id, methods)
        for run in runs:
            await self.run_job(run.id)
        return [await self.get_run_summary(run.id) for run in runs]
