from __future__ import annotations

from ips_db import LangIdTrainingJob
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lang_id import LangIdError
from app.infrastructure.lang_id_client import LangIdServiceClient
from app.infrastructure.repositories.chunk_embeddings import ChunkEmbeddingRepository
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.lang_id import LangIdProfileRepository, LangIdTrainingJobRepository
from app.infrastructure.repositories.search_models import SearchModelRepository

from .stored_embeddings import stored_vectors_for

NEURAL_TOTAL_EPOCHS = 200
NEURAL_EPOCH_CHUNK = 10


class LangIdTrainingService:

    def __init__(self, session: AsyncSession, *, lang_id_client: LangIdServiceClient | None = None) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._profiles = LangIdProfileRepository(session)
        self._training_jobs = LangIdTrainingJobRepository(session)
        self._chunk_embeddings = ChunkEmbeddingRepository(session)
        self._search_models = SearchModelRepository(session)
        self._lang_id = lang_id_client or LangIdServiceClient()

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
                vectors_by_language[language] = await stored_vectors_for(
                    documents, chunk_embeddings=self._chunk_embeddings, search_models=self._search_models
                )

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
        except Exception as exc:
            message = str(exc) or type(exc).__name__
            await self._training_jobs.mark_failed(job_id, error_message=f"{type(exc).__name__}: {message}")
