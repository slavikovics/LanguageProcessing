import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.summarization import DocumentSummarizationService, SummarizationTestRunService
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.domain.summarization import SummarizationError
from app.interface.schemas import (
    DocumentSummaryOut,
    KeywordGroupOut,
    PolishSummaryOut,
    PolishSummaryRequest,
    SummarizationCompareResponseOut,
    SummarizationRunCreate,
    SummarizationRunOut,
    SummarizationRunSummaryOut,
    SummarizeDocumentRequest,
    SummarizeDocumentResponseOut,
    SummaryOutcomeOut,
)

router = APIRouter(tags=["summarization"])

_TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled"}


def _raise_for_summarization_error(exc: SummarizationError) -> None:
    status = 404 if "not found" in str(exc) else 422
    raise HTTPException(status_code=status, detail=str(exc)) from exc


async def _run_summarization_run(run_id: int) -> None:
    async with SessionLocal() as session:
        await SummarizationTestRunService(session).run_job(run_id)


@router.post(
    "/documents/{document_id}/summarize", response_model=SummarizeDocumentResponseOut
)
async def summarize_document(
    document_id: int, payload: SummarizeDocumentRequest, db: AsyncSession = Depends(get_db)
) -> SummarizeDocumentResponseOut:
    service = DocumentSummarizationService(db)
    try:
        keywords, outcomes = await service.summarize_document(
            document_id,
            methods=payload.methods,
            sentence_count=payload.sentence_count,
            keyword_count=payload.keyword_count,
            query=payload.query,
        )
    except SummarizationError as exc:
        _raise_for_summarization_error(exc)
    return SummarizeDocumentResponseOut(
        document_id=document_id,
        keywords=[KeywordGroupOut(term=g.term, children=g.children) for g in keywords],
        results=[
            SummaryOutcomeOut(
                method=outcome.method,
                sentences=[vars(s) for s in outcome.sentences],
                total_sentences=outcome.total_sentences,
                elapsed_ms=outcome.elapsed_ms,
                compression_ratio=outcome.compression_ratio,
            )
            for outcome in outcomes
        ],
    )


@router.get("/documents/{document_id}/summaries", response_model=list[DocumentSummaryOut])
async def list_document_summaries(
    document_id: int, db: AsyncSession = Depends(get_db)
) -> list[DocumentSummaryOut]:
    service = DocumentSummarizationService(db)
    return await service.list_summaries(document_id)


@router.post("/summaries/{summary_id}/polish", response_model=PolishSummaryOut)
async def polish_summary(
    summary_id: int, payload: PolishSummaryRequest, db: AsyncSession = Depends(get_db)
) -> PolishSummaryOut:
    service = DocumentSummarizationService(db)
    try:
        polished_markdown, model = await service.polish_summary(summary_id, language=payload.language)
    except SummarizationError as exc:
        _raise_for_summarization_error(exc)
    return PolishSummaryOut(document_summary_id=summary_id, model=model, polished_markdown=polished_markdown)


@router.post("/summarization/runs", response_model=list[SummarizationRunOut], status_code=201)
async def create_runs(
    payload: SummarizationRunCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> list[SummarizationRunOut]:
    service = SummarizationTestRunService(db)
    try:
        runs = await service.start_run(payload.collection_id, payload.methods)
    except SummarizationError as exc:
        _raise_for_summarization_error(exc)
    for run in runs:
        background_tasks.add_task(_run_summarization_run, run.id)
    return runs


@router.post("/summarization/runs/{run_id}/cancel", response_model=SummarizationRunOut)
async def cancel_run(run_id: int, db: AsyncSession = Depends(get_db)) -> SummarizationRunOut:
    service = SummarizationTestRunService(db)
    try:
        return await service.cancel_run(run_id)
    except SummarizationError as exc:
        _raise_for_summarization_error(exc)


@router.get("/summarization/runs/{run_id}", response_model=SummarizationRunOut)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)) -> SummarizationRunOut:
    service = SummarizationTestRunService(db)
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="summarization run not found")
    return run


@router.get(
    "/collections/{collection_id}/summarization/runs", response_model=list[SummarizationRunOut]
)
async def list_runs_by_collection(
    collection_id: int, db: AsyncSession = Depends(get_db)
) -> list[SummarizationRunOut]:
    service = SummarizationTestRunService(db)
    return await service.list_runs_by_collection(collection_id)


@router.websocket("/summarization/runs/ws/{run_id}")
async def summarization_run_progress_ws(websocket: WebSocket, run_id: int) -> None:
    await websocket.accept()
    settings = get_settings()
    last_payload: str | None = None
    try:
        while True:
            async with SessionLocal() as session:
                service = SummarizationTestRunService(session)
                run = await service.get_run(run_id)
                if run is None:
                    await websocket.send_json({"error": "summarization run not found"})
                    break
                payload_model = SummarizationRunOut.model_validate(run)

            payload = payload_model.model_dump_json()
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

            if payload_model.status in _TERMINAL_RUN_STATUSES:
                break
            await asyncio.sleep(settings.crawl_progress_poll_interval_seconds)
    except WebSocketDisconnect:
        pass


@router.get("/summarization/runs/{run_id}/results", response_model=list[DocumentSummaryOut])
async def get_run_results(run_id: int, db: AsyncSession = Depends(get_db)) -> list[DocumentSummaryOut]:
    service = SummarizationTestRunService(db)
    return await service.get_run_results(run_id)


@router.get("/summarization/runs/{run_id}/summary", response_model=SummarizationRunSummaryOut)
async def get_run_summary(run_id: int, db: AsyncSession = Depends(get_db)) -> SummarizationRunSummaryOut:
    service = SummarizationTestRunService(db)
    try:
        return await service.get_run_summary(run_id)
    except SummarizationError as exc:
        _raise_for_summarization_error(exc)


@router.get("/summarization/compare", response_model=SummarizationCompareResponseOut)
async def compare(
    collection_id: int,
    methods: str = "algorithmic,textrank,embeddings",
    db: AsyncSession = Depends(get_db),
) -> SummarizationCompareResponseOut:
    service = SummarizationTestRunService(db)
    method_list = [m for m in methods.split(",") if m]
    summaries = await service.compare(collection_id, method_list)
    return {"summaries": summaries}
