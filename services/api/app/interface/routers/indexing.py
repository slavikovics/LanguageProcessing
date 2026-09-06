import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.indexing import IndexingService, IndexJobNotFound
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.domain.enums import IndexJobStatus
from app.domain.indexing import IndexingError
from app.interface.schemas import IndexJobOut

router = APIRouter(tags=["indexing"])

_TERMINAL_STATUSES = {IndexJobStatus.COMPLETED.value, IndexJobStatus.FAILED.value}


async def _run_index_job(job_id: int) -> None:
    """Runs in the background after the response is sent, with its own DB
    session — the request-scoped session from Depends(get_db) is already
    closed by then."""
    async with SessionLocal() as session:
        await IndexingService(session).run_job(job_id)


@router.post("/collections/{collection_id}/index-jobs", response_model=IndexJobOut, status_code=201)
async def create_index_job(
    collection_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> IndexJobOut:
    service = IndexingService(db)
    try:
        job = await service.start_job(collection_id)
    except IndexingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    background_tasks.add_task(_run_index_job, job.id)
    return job


@router.get("/index-jobs/{job_id}", response_model=IndexJobOut)
async def get_index_job(job_id: int, db: AsyncSession = Depends(get_db)) -> IndexJobOut:
    service = IndexingService(db)
    job = await service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="index job not found")
    return job


@router.get("/collections/{collection_id}/index-jobs/latest", response_model=IndexJobOut | None)
async def get_latest_index_job(collection_id: int, db: AsyncSession = Depends(get_db)) -> IndexJobOut | None:
    service = IndexingService(db)
    return await service.get_latest_job(collection_id)


@router.post("/index-jobs/{job_id}/cancel", response_model=IndexJobOut)
async def cancel_index_job(job_id: int, db: AsyncSession = Depends(get_db)) -> IndexJobOut:
    service = IndexingService(db)
    try:
        await service.cancel_job(job_id)
    except IndexJobNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IndexingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    job = await service.get_job(job_id)
    assert job is not None
    return job


@router.websocket("/index-jobs/ws/{job_id}")
async def index_job_progress_ws(websocket: WebSocket, job_id: int) -> None:
    """Polls index_jobs and pushes diffs; the frontend falls back to plain
    GET /index-jobs/{id} polling if this connection drops."""
    await websocket.accept()
    settings = get_settings()
    last_payload: str | None = None
    try:
        while True:
            async with SessionLocal() as session:
                service = IndexingService(session)
                job = await service.get_job(job_id)
                if job is None:
                    await websocket.send_json({"error": "index job not found"})
                    break
                payload_model = IndexJobOut.model_validate(job)

            payload = payload_model.model_dump_json()
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

            if payload_model.status in _TERMINAL_STATUSES:
                break
            await asyncio.sleep(settings.crawl_progress_poll_interval_seconds)
    except WebSocketDisconnect:
        pass
