from __future__ import annotations

import httpx
from ips_db import Document, LangIdResult, LangIdRun, LangIdTrainingJob
from nlp_core.content_extraction import extract_main_content
from nlp_core.tokenization import clean_html
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.indexing import chunk_text
from app.domain.lang_id import (
    METHODS,
    IdentificationOutcome,
    LangIdError,
    LangIdRunSummary,
    split_train_test,
    summarize_results,
)
from app.infrastructure.lang_id_client import LangIdServiceClient
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.chunk_embeddings import ChunkEmbeddingRepository
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.lang_id import (
    LangIdProfileRepository,
    LangIdResultRepository,
    LangIdRunMetricRepository,
    LangIdRunRepository,
    LangIdTrainingJobRepository,
)
from app.infrastructure.repositories.search_models import SearchModelRepository

# 200 total epochs is enough for a linear classifier to converge on a few
# hundred 4096-dim vectors; chunked into small steps so the training job's
# progress bar and loss/accuracy readout visibly move rather than jumping
# straight from 0% to 100%.
NEURAL_TOTAL_EPOCHS = 200
NEURAL_EPOCH_CHUNK = 10


class LanguageIdentificationService:
    """Orchestrates LR2's three language-ID methods: profile building,
    ad-hoc identification (by document/URL/pasted text), neural training
    with live progress, and test-collection runs with aggregate stats.

    All three methods' actual math lives in lang-id-service (via
    LangIdServiceClient); this service only loads/persists data and decides
    which profiles to compare a piece of text against. For corpus documents
    (training and test-collection runs), the neural method reuses embeddings
    already computed and stored during search indexing (see
    `_stored_vectors_for`) rather than re-requesting them from OpenRouter —
    indexing a collection is a prerequisite for its neural training/testing.
    Ad-hoc classification of a URL/pasted text/uploaded HTML has no indexed
    document to reuse, so that path still embeds live via nlp-service.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        nlp_client: NlpServiceClient | None = None,
        lang_id_client: LangIdServiceClient | None = None,
    ) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._profiles = LangIdProfileRepository(session)
        self._training_jobs = LangIdTrainingJobRepository(session)
        self._runs = LangIdRunRepository(session)
        self._results = LangIdResultRepository(session)
        self._run_metrics = LangIdRunMetricRepository(session)
        self._chunk_embeddings = ChunkEmbeddingRepository(session)
        self._search_models = SearchModelRepository(session)
        self._nlp = nlp_client or NlpServiceClient()
        self._lang_id = lang_id_client or LangIdServiceClient()

    async def _stored_vectors_for(self, documents: list[Document]) -> list[list[float]]:
        """Reuses each document's chunk_index=0 embedding, computed once
        during search indexing, instead of re-requesting it from OpenRouter —
        indexing the collection is a prerequisite for both neural training
        and neural testing precisely so this lookup can be instant."""
        active_models = await self._search_models.list_active()
        dense_model = next((m for m in active_models if m.kind == "dense_embedding"), None)
        if dense_model is None:
            raise LangIdError("no active dense-embedding search model — index a collection first")

        document_ids = [document.id for document in documents]
        vectors_by_id = await self._chunk_embeddings.get_first_chunk_vectors(document_ids, dense_model.id)
        missing = [document.id for document in documents if document.id not in vectors_by_id]
        if missing:
            raise LangIdError(
                f"{len(missing)} document(s) have no stored embedding yet — index their "
                "collection(s) before training or testing the neural classifier"
            )
        return [vectors_by_id[document.id] for document in documents]

    # -- labeling / train-test split -----------------------------------

    async def set_language_label(
        self, document_id: int, *, confirmed_language: str | None, corpus_split: str | None
    ):
        document = await self._documents.get(document_id)
        if document is None:
            raise LangIdError(f"document {document_id} not found")
        updated = await self._documents.set_language_label(
            document, confirmed_language=confirmed_language, corpus_split=corpus_split
        )
        await self._session.commit()
        return updated

    async def auto_split(self, collection_id: int, *, test_ratio: float = 0.2) -> dict[str, int]:
        """Bulk-assigns every confirmed-but-unsplit document in the
        collection to train/test, stratified per language — the one-click
        alternative to clicking "Обучение"/"Тест" on each document by hand.
        Leaves documents someone already split alone."""
        documents = await self._documents.list_confirmed_without_split(collection_id)
        if not documents:
            raise LangIdError(
                "нет размеченных документов без выборки — подтвердите язык хотя бы у одного "
                "документа, прежде чем разбивать автоматически"
            )
        by_language: dict[str, list[int]] = {}
        for document in documents:
            by_language.setdefault(document.confirmed_language, []).append(document.id)

        train_ids, test_ids = split_train_test(by_language, test_ratio=test_ratio)
        await self._documents.bulk_set_corpus_split(train_ids=train_ids, test_ids=test_ids)
        await self._session.commit()
        return {"train_assigned": len(train_ids), "test_assigned": len(test_ids)}

    async def get_label_progress(self, collection_id: int) -> dict[str, int]:
        total = await self._documents.count_by_collection(collection_id)
        unlabeled = await self._documents.count_unlabeled_by_collection(collection_id)
        train_count = await self._documents.count_by_collection_and_split(collection_id, "train")
        test_count = await self._documents.count_by_collection_and_split(collection_id, "test")
        return {
            "total": total,
            "labeled": total - unlabeled,
            "unlabeled": unlabeled,
            "train_count": train_count,
            "test_count": test_count,
        }

    # -- profiles ------------------------------------------------------

    async def list_profiles(self):
        return await self._profiles.list_all()

    async def build_lexical_profile(self, method: str, language: str):
        if method not in ("frequent_words", "alphabetic"):
            raise LangIdError(f"'{method}' is not a lexical profile method")
        documents = await self._documents.list_training_documents(language)
        if not documents:
            confirmed_count = await self._documents.count_confirmed(language)
            if confirmed_count == 0:
                raise LangIdError(
                    f"no documents are confirmed as '{language}' yet — label some in the "
                    "Разметка tab before building this profile"
                )
            raise LangIdError(
                f"{confirmed_count} document(s) are confirmed as '{language}', but none are "
                "assigned to the training split — set corpus_split='train' for at least one "
                "via the label editor"
            )
        texts = [document.clean_text for document in documents]

        if method == "frequent_words":
            top_words = await self._lang_id.build_frequent_words_profile(texts)
            profile_data = {"top_words": top_words}
        else:
            frequencies = await self._lang_id.build_alphabetic_profile(texts)
            profile_data = {"frequencies": frequencies}

        profile = await self._profiles.upsert(
            method=method,
            language=language,
            profile_data=profile_data,
            source_document_count=len(documents),
            source_char_count=sum(len(text) for text in texts),
        )
        await self._session.commit()
        return profile

    async def _load_lexical_profiles(self, method: str) -> dict:
        key = "top_words" if method == "frequent_words" else "frequencies"
        rows = await self._profiles.list_by_method(method)
        return {row.language: row.profile_data[key] for row in rows if row.language is not None}

    # -- neural training -------------------------------------------------

    async def start_neural_training(self) -> LangIdTrainingJob:
        languages = await self._documents.list_distinct_training_languages()
        if len(languages) < 2:
            raise LangIdError(
                "need training documents confirmed in at least 2 languages to train the neural classifier"
            )
        job = await self._training_jobs.create()
        await self._session.commit()
        return job

    async def get_training_job(self, job_id: int) -> LangIdTrainingJob | None:
        return await self._training_jobs.get(job_id)

    async def get_latest_training_job(self) -> LangIdTrainingJob | None:
        return await self._training_jobs.latest()

    async def run_neural_training(self, job_id: int) -> None:
        job = await self._training_jobs.get(job_id)
        if job is None:
            return
        try:
            languages = await self._documents.list_distinct_training_languages()
            vectors_by_language: dict[str, list[list[float]]] = {}
            for language in languages:
                documents = await self._documents.list_training_documents(language)
                vectors_by_language[language] = await self._stored_vectors_for(documents)

            started = await self._training_jobs.mark_running(job_id, epochs_total=NEURAL_TOTAL_EPOCHS)
            if not started:
                return

            weights: list[list[float]] | None = None
            bias: list[float] | None = None
            classes: list[str] | None = None
            loss_curve: list[float] = []
            epochs_done = 0

            while epochs_done < NEURAL_TOTAL_EPOCHS:
                chunk = min(NEURAL_EPOCH_CHUNK, NEURAL_TOTAL_EPOCHS - epochs_done)
                step = await self._lang_id.train_neural_step(
                    vectors_by_language, weights=weights, bias=bias, classes=classes, epochs=chunk
                )
                weights, bias, classes = step["weights"], step["bias"], step["classes"]
                loss_curve.extend(step["loss_curve_chunk"])
                epochs_done += chunk
                await self._training_jobs.update_progress(
                    job_id,
                    epochs_completed=epochs_done,
                    current_loss=step["loss_curve_chunk"][-1],
                    current_train_accuracy=step["train_accuracy"],
                )

            source_document_count = sum(len(vectors) for vectors in vectors_by_language.values())
            await self._profiles.upsert(
                method="neural",
                language=None,
                profile_data={"weights": weights, "bias": bias, "classes": classes, "loss_curve": loss_curve},
                source_document_count=source_document_count,
                source_char_count=0,
            )
            await self._session.commit()
            await self._training_jobs.mark_completed(job_id)
        except Exception as exc:  # pragma: no cover - top-level safety net
            message = str(exc) or type(exc).__name__
            await self._training_jobs.mark_failed(job_id, error_message=f"{type(exc).__name__}: {message}")

    # -- identification ----------------------------------------------------

    async def identify_text(
        self, text: str, methods: list[str] | None = None
    ) -> list[IdentificationOutcome]:
        """Core reusable primitive: every other identify_* method reduces to
        this once it has plain text in hand. Silently skips a method that
        doesn't have enough profiles to make a comparison yet (fewer than 2
        languages for the lexical methods, or no trained neural classifier)
        rather than failing the whole call."""
        outcomes: list[IdentificationOutcome] = []
        for method in methods or METHODS:
            if method == "frequent_words":
                profiles = await self._load_lexical_profiles("frequent_words")
                if len(profiles) < 2:
                    continue
                result = await self._lang_id.identify_frequent_words(profiles, text)
            elif method == "alphabetic":
                profiles = await self._load_lexical_profiles("alphabetic")
                if len(profiles) < 2:
                    continue
                result = await self._lang_id.identify_alphabetic(profiles, text)
            elif method == "neural":
                profile = await self._profiles.get("neural", None)
                if profile is None:
                    continue
                data = profile.profile_data
                representative_text = (chunk_text(text) or [""])[0]
                vector = (await self._nlp.embed_documents([representative_text]))[0]
                result = await self._lang_id.identify_neural(
                    data["weights"], data["bias"], data["classes"], vector
                )
            else:
                raise LangIdError(f"unknown method '{method}'")

            outcomes.append(
                IdentificationOutcome(
                    method=method,
                    predicted_language=result["predicted_language"],
                    distances=result["distances"],
                    elapsed_ms=result["elapsed_ms"],
                )
            )
        return outcomes

    async def identify_document(
        self, document_id: int, methods: list[str] | None = None
    ) -> list[IdentificationOutcome]:
        document = await self._documents.get(document_id)
        if document is None:
            raise LangIdError(f"document {document_id} not found")
        return await self.identify_text(document.clean_text, methods)

    async def identify_url(
        self, url: str, methods: list[str] | None = None
    ) -> list[IdentificationOutcome]:
        """Ad-hoc, one-off classification — fetches and extracts the page
        but does not persist a Document row; this is a scratch check, not a
        corpus addition."""
        headers = {"User-Agent": get_settings().crawler_user_agent}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
        text = extract_main_content(response.text)
        return await self.identify_text(text, methods)

    async def identify_raw_html(
        self, html: str, methods: list[str] | None = None
    ) -> list[IdentificationOutcome]:
        """Backs the paste-text-or-upload-HTML UI — no persistence either."""
        return await self.identify_text(clean_html(html), methods)

    # -- test-collection runs -----------------------------------------------

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
        """Classifies every test document under one method. The neural method
        reuses each document's embedding already computed and stored during
        search indexing (see `_stored_vectors_for`) instead of re-requesting
        it from OpenRouter — unlike the lexical methods, whose per-document
        cost is pure in-process math in lang-id-service and is fine to run
        one document at a time."""
        if method != "neural":
            outcomes: dict[int, IdentificationOutcome] = {}
            for document in documents:
                found = await self.identify_text(document.clean_text, [method])
                if found:
                    outcomes[document.id] = found[0]
            return outcomes

        profile = await self._profiles.get("neural", None)
        if profile is None:
            return {}
        data = profile.profile_data
        vectors = await self._stored_vectors_for(documents)
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
        """Like `compare`, but starts fresh runs for every requested method
        and waits for them to finish first — the classification-quality
        analogue of MetricsService.rerun_all_and_compare, so numbers reflect
        the current profiles/classifier rather than a possibly stale run."""
        runs = await self.start_run(collection_id, methods)
        for run in runs:
            await self.run_job(run.id)
        return [await self.get_run_summary(run.id) for run in runs]
