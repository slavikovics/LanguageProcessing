import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.crawl_jobs import CrawlJobNotFound, CrawlJobService
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.domain.crawl_jobs import InvalidCrawlJobConfig
from app.domain.enums import CrawlJobStatus
from app.interface.schemas import CrawlJobCreate, CrawlJobOut, CrawlJobProgressOut

router = APIRouter(prefix="/crawl-jobs", tags=["crawl-jobs"])

_TERMINAL_STATUSES = {
    CrawlJobStatus.COMPLETED.value,
    CrawlJobStatus.FAILED.value,
    CrawlJobStatus.CANCELLED.value,
}


@router.post("", response_model=CrawlJobOut, status_code=201)
async def create_crawl_job(
    payload: CrawlJobCreate, db: AsyncSession = Depends(get_db)
) -> CrawlJobOut:
    service = CrawlJobService(db)
    try:
        return await service.create_job(
            collection_id=payload.collection_id,
            seed_urls=payload.seed_urls,
            max_documents=payload.max_documents,
            max_depth=payload.max_depth,
        )
    except InvalidCrawlJobConfig as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[CrawlJobOut])
async def list_crawl_jobs(
    collection_id: int | None = Query(default=None), db: AsyncSession = Depends(get_db)
) -> list[CrawlJobOut]:
    service = CrawlJobService(db)
    return await service.list_jobs(collection_id=collection_id)


@router.get("/{job_id}", response_model=CrawlJobProgressOut)
async def get_crawl_job(job_id: int, db: AsyncSession = Depends(get_db)) -> CrawlJobProgressOut:
    service = CrawlJobService(db)
    job, recent_urls = await service.get_progress(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="crawl job not found")
    return CrawlJobProgressOut(job=job, recent_urls=recent_urls)


@router.post("/{job_id}/cancel", response_model=CrawlJobOut)
async def cancel_crawl_job(job_id: int, db: AsyncSession = Depends(get_db)) -> CrawlJobOut:
    service = CrawlJobService(db)
    try:
        return await service.cancel_job(job_id)
    except CrawlJobNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidCrawlJobConfig as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.websocket("/ws/{job_id}")
async def crawl_job_progress_ws(websocket: WebSocket, job_id: int) -> None:
    """Pushes CrawlJobProgressOut diffs by polling the crawl_jobs/crawl_urls
    tables — the DB stays the single source of truth (see docs/PROJECT_PLAN.md,
    3.1); the frontend can fall back to plain GET /crawl-jobs/{id} polling if
    this connection drops.
    """
    await websocket.accept()
    settings = get_settings()
    last_payload: str | None = None
    try:
        while True:
            async with SessionLocal() as session:
                service = CrawlJobService(session)
                job, recent_urls = await service.get_progress(job_id)
                if job is None:
                    await websocket.send_json({"error": "crawl job not found"})
                    break
                progress = CrawlJobProgressOut(job=job, recent_urls=recent_urls)

            payload = progress.model_dump_json()
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

            if progress.job.status in _TERMINAL_STATUSES:
                break
            await asyncio.sleep(settings.crawl_progress_poll_interval_seconds)
    except WebSocketDisconnect:
        pass
