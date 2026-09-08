from __future__ import annotations

import datetime as dt

from ips_db import LangIdProfile, LangIdResult, LangIdRun, LangIdRunMetric, LangIdTrainingJob
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import LangIdRunStatus, LangIdTrainingJobStatus


class LangIdProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        method: str,
        language: str | None,
        profile_data: dict,
        source_document_count: int,
        source_char_count: int,
    ) -> LangIdProfile:
        language_clause = (
            LangIdProfile.language.is_(None) if language is None else LangIdProfile.language == language
        )
        result = await self._session.execute(
            select(LangIdProfile).where(LangIdProfile.method == method, language_clause)
        )
        profile = result.scalars().first()
        if profile is not None:
            profile.profile_data = profile_data
            profile.source_document_count = source_document_count
            profile.source_char_count = source_char_count
            profile.built_at = dt.datetime.utcnow()
        else:
            profile = LangIdProfile(
                method=method,
                language=language,
                profile_data=profile_data,
                source_document_count=source_document_count,
                source_char_count=source_char_count,
            )
            self._session.add(profile)
        await self._session.flush()
        return profile

    async def get(self, method: str, language: str | None) -> LangIdProfile | None:
        language_clause = (
            LangIdProfile.language.is_(None) if language is None else LangIdProfile.language == language
        )
        result = await self._session.execute(
            select(LangIdProfile).where(LangIdProfile.method == method, language_clause)
        )
        return result.scalars().first()

    async def list_all(self) -> list[LangIdProfile]:
        result = await self._session.execute(select(LangIdProfile).order_by(LangIdProfile.method))
        return list(result.scalars().all())

    async def list_by_method(self, method: str) -> list[LangIdProfile]:
        result = await self._session.execute(
            select(LangIdProfile).where(LangIdProfile.method == method)
        )
        return list(result.scalars().all())


class LangIdTrainingJobRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self) -> LangIdTrainingJob:
        job = LangIdTrainingJob(status=LangIdTrainingJobStatus.PENDING.value)
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> LangIdTrainingJob | None:
        return await self._session.get(LangIdTrainingJob, job_id)

    async def latest(self) -> LangIdTrainingJob | None:
        result = await self._session.execute(
            select(LangIdTrainingJob).order_by(LangIdTrainingJob.id.desc()).limit(1)
        )
        return result.scalars().first()

    async def mark_running(self, job_id: int, *, epochs_total: int) -> bool:
        result = await self._session.execute(
            update(LangIdTrainingJob)
            .where(
                LangIdTrainingJob.id == job_id,
                LangIdTrainingJob.status == LangIdTrainingJobStatus.PENDING.value,
            )
            .values(
                status=LangIdTrainingJobStatus.RUNNING.value,
                epochs_total=epochs_total,
                started_at=dt.datetime.utcnow(),
            )
        )
        await self._session.commit()
        return result.rowcount > 0

    async def update_progress(
        self, job_id: int, *, epochs_completed: int, current_loss: float, current_train_accuracy: float
    ) -> None:
        job = await self._session.get(LangIdTrainingJob, job_id)
        if job is None:
            return
        job.epochs_completed = epochs_completed
        job.current_loss = current_loss
        job.current_train_accuracy = current_train_accuracy
        await self._session.commit()

    async def mark_completed(self, job_id: int) -> None:
        job = await self._session.get(LangIdTrainingJob, job_id)
        if job is None:
            return
        job.status = LangIdTrainingJobStatus.COMPLETED.value
        job.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def mark_failed(self, job_id: int, *, error_message: str) -> None:
        job = await self._session.get(LangIdTrainingJob, job_id)
        if job is None:
            return
        job.status = LangIdTrainingJobStatus.FAILED.value
        job.error_message = error_message[:1000]
        job.finished_at = dt.datetime.utcnow()
        await self._session.commit()


class LangIdRunRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, collection_id: int, method: str) -> LangIdRun:
        run = LangIdRun(collection_id=collection_id, method=method, status=LangIdRunStatus.PENDING.value)
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, run_id: int) -> LangIdRun | None:
        return await self._session.get(LangIdRun, run_id)

    async def list_by_collection(self, collection_id: int) -> list[LangIdRun]:
        result = await self._session.execute(
            select(LangIdRun).where(LangIdRun.collection_id == collection_id).order_by(LangIdRun.id.desc())
        )
        return list(result.scalars().all())

    async def mark_running(self, run_id: int, *, documents_total: int) -> bool:
        result = await self._session.execute(
            update(LangIdRun)
            .where(LangIdRun.id == run_id, LangIdRun.status == LangIdRunStatus.PENDING.value)
            .values(
                status=LangIdRunStatus.RUNNING.value,
                documents_total=documents_total,
                started_at=dt.datetime.utcnow(),
            )
        )
        await self._session.commit()
        return result.rowcount > 0

    async def update_progress(self, run_id: int, *, documents_processed: int) -> None:
        run = await self._session.get(LangIdRun, run_id)
        if run is None:
            return
        run.documents_processed = documents_processed
        await self._session.commit()

    async def mark_completed(self, run_id: int) -> None:
        run = await self._session.get(LangIdRun, run_id)
        if run is None:
            return
        run.status = LangIdRunStatus.COMPLETED.value
        run.finished_at = dt.datetime.utcnow()
        await self._session.commit()

    async def mark_failed(self, run_id: int, *, error_message: str) -> None:
        run = await self._session.get(LangIdRun, run_id)
        if run is None:
            return
        run.status = LangIdRunStatus.FAILED.value
        run.error_message = error_message[:1000]
        run.finished_at = dt.datetime.utcnow()
        await self._session.commit()


class LangIdResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_write(self, rows: list[dict[str, object]]) -> None:
        if not rows:
            return
        await self._session.execute(insert(LangIdResult), rows)

    async def list_for_run(self, run_id: int) -> list[LangIdResult]:
        result = await self._session.execute(
            select(LangIdResult).where(LangIdResult.run_id == run_id).order_by(LangIdResult.id)
        )
        return list(result.scalars().all())

    async def clear_for_run(self, run_id: int) -> None:
        await self._session.execute(delete(LangIdResult).where(LangIdResult.run_id == run_id))


class LangIdRunMetricRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_run(self, run_id: int, metrics: dict[str, float]) -> None:
        await self._session.execute(delete(LangIdRunMetric).where(LangIdRunMetric.run_id == run_id))
        if metrics:
            rows = [{"run_id": run_id, "metric_name": name, "value": value} for name, value in metrics.items()]
            await self._session.execute(insert(LangIdRunMetric), rows)

    async def list_for_run(self, run_id: int) -> list[LangIdRunMetric]:
        result = await self._session.execute(
            select(LangIdRunMetric).where(LangIdRunMetric.run_id == run_id)
        )
        return list(result.scalars().all())
