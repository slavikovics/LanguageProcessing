import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.translation import (
    TranslationDictionaryService,
    TranslationService,
    TranslationTestRunService,
)
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.domain.translation import TranslationError
from app.interface.schemas import (
    ParseSentenceRequest,
    ParseSentenceResponseOut,
    SentenceListOut,
    SyntaxTokenOut,
    TranslateRequest,
    TranslationDictionaryEntryCreate,
    TranslationDictionaryEntryOut,
    TranslationDictionaryEntryUpdate,
    TranslationDictionaryPageOut,
    TranslationRunOut,
    TranslationRunSummaryOut,
    TranslationRunWordOut,
    TranslationTestRunCreate,
    TranslationTestRunOut,
)

router = APIRouter(tags=["translation"])

_TERMINAL_TEST_RUN_STATUSES = {"completed", "failed", "cancelled"}


def _raise_for_translation_error(exc: TranslationError) -> None:
    status = 404 if "not found" in str(exc) else 422
    raise HTTPException(status_code=status, detail=str(exc)) from exc


async def _run_translation_test_run(run_id: int) -> None:
    async with SessionLocal() as session:
        await TranslationTestRunService(session).run_job(run_id)


@router.post("/translation/runs", response_model=TranslationRunOut, status_code=201)
async def create_translation_run(
    payload: TranslateRequest, db: AsyncSession = Depends(get_db)
) -> TranslationRunOut:
    service = TranslationService(db)
    try:
        return await service.translate(
            document_id=payload.document_id,
            text=payload.text,
            collection_id=payload.collection_id,
            source_lang=payload.source_lang,
            target_lang=payload.target_lang,
            method=payload.method,
        )
    except TranslationError as exc:
        _raise_for_translation_error(exc)


@router.get(
    "/translation/collections/{collection_id}/runs/latest",
    response_model=TranslationRunOut | None,
)
async def get_latest_translation_run_for_collection(
    collection_id: int, method: str | None = None, db: AsyncSession = Depends(get_db)
) -> TranslationRunOut | None:
    service = TranslationService(db)
    return await service.get_latest_for_collection(collection_id, method=method)


@router.get("/translation/runs/{run_id}", response_model=TranslationRunOut)
async def get_translation_run(run_id: int, db: AsyncSession = Depends(get_db)) -> TranslationRunOut:
    service = TranslationService(db)
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="translation run not found")
    return run


@router.get("/translation/runs", response_model=list[TranslationRunOut])
async def list_translation_runs(
    limit: int = 20, db: AsyncSession = Depends(get_db)
) -> list[TranslationRunOut]:
    service = TranslationService(db)
    return await service.list_runs(limit=limit)


@router.get("/translation/runs/{run_id}/words", response_model=list[TranslationRunWordOut])
async def get_translation_run_words(
    run_id: int, db: AsyncSession = Depends(get_db)
) -> list[TranslationRunWordOut]:
    service = TranslationService(db)
    try:
        return await service.get_run_words(run_id)
    except TranslationError as exc:
        _raise_for_translation_error(exc)


@router.get("/translation/runs/{run_id}/sentences", response_model=SentenceListOut)
async def get_translation_run_sentences(
    run_id: int, db: AsyncSession = Depends(get_db)
) -> SentenceListOut:
    service = TranslationService(db)
    try:
        sentences = await service.list_sentences(run_id)
    except TranslationError as exc:
        _raise_for_translation_error(exc)
    return SentenceListOut(sentences=sentences)


@router.post("/translation/parse-sentence", response_model=ParseSentenceResponseOut)
async def parse_sentence(
    payload: ParseSentenceRequest, db: AsyncSession = Depends(get_db)
) -> ParseSentenceResponseOut:
    service = TranslationService(db)
    try:
        tokens = await service.parse_sentence(payload.text)
    except TranslationError as exc:
        _raise_for_translation_error(exc)
    return ParseSentenceResponseOut(tokens=[SyntaxTokenOut(**tok) for tok in tokens])


@router.post("/translation/test-runs", response_model=TranslationTestRunOut, status_code=201)
async def create_translation_test_run(
    payload: TranslationTestRunCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> TranslationTestRunOut:
    service = TranslationTestRunService(db)
    try:
        run = await service.start_run(
            payload.collection_id,
            source_lang=payload.source_lang,
            target_lang=payload.target_lang,
            method=payload.method,
        )
    except TranslationError as exc:
        _raise_for_translation_error(exc)
    background_tasks.add_task(_run_translation_test_run, run.id)
    return run


@router.post("/translation/test-runs/{run_id}/cancel", response_model=TranslationTestRunOut)
async def cancel_translation_test_run(run_id: int, db: AsyncSession = Depends(get_db)) -> TranslationTestRunOut:
    service = TranslationTestRunService(db)
    try:
        return await service.cancel_run(run_id)
    except TranslationError as exc:
        _raise_for_translation_error(exc)


@router.get("/translation/test-runs/{run_id}", response_model=TranslationTestRunOut)
async def get_translation_test_run(run_id: int, db: AsyncSession = Depends(get_db)) -> TranslationTestRunOut:
    service = TranslationTestRunService(db)
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="translation test run not found")
    return run


@router.get(
    "/collections/{collection_id}/translation/test-runs", response_model=list[TranslationTestRunOut]
)
async def list_translation_test_runs_by_collection(
    collection_id: int, method: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[TranslationTestRunOut]:
    service = TranslationTestRunService(db)
    return await service.list_runs_by_collection(collection_id, method=method)


@router.websocket("/translation/test-runs/ws/{run_id}")
async def translation_test_run_progress_ws(websocket: WebSocket, run_id: int) -> None:
    await websocket.accept()
    settings = get_settings()
    last_payload: str | None = None
    try:
        while True:
            async with SessionLocal() as session:
                service = TranslationTestRunService(session)
                run = await service.get_run(run_id)
                if run is None:
                    await websocket.send_json({"error": "translation test run not found"})
                    break
                payload_model = TranslationTestRunOut.model_validate(run)

            payload = payload_model.model_dump_json()
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

            if payload_model.status in _TERMINAL_TEST_RUN_STATUSES:
                break
            await asyncio.sleep(settings.crawl_progress_poll_interval_seconds)
    except WebSocketDisconnect:
        pass


@router.get("/translation/test-runs/{run_id}/results", response_model=list[TranslationRunOut])
async def get_translation_test_run_results(
    run_id: int, db: AsyncSession = Depends(get_db)
) -> list[TranslationRunOut]:
    service = TranslationTestRunService(db)
    return await service.get_run_results(run_id)


@router.get("/translation/test-runs/{run_id}/summary", response_model=TranslationRunSummaryOut)
async def get_translation_test_run_summary(
    run_id: int, db: AsyncSession = Depends(get_db)
) -> TranslationRunSummaryOut:
    service = TranslationTestRunService(db)
    try:
        return await service.get_run_summary(run_id)
    except TranslationError as exc:
        _raise_for_translation_error(exc)


@router.get("/translation/dictionary", response_model=TranslationDictionaryPageOut)
async def list_dictionary_entries(
    source_lang: str | None = None,
    target_lang: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> TranslationDictionaryPageOut:
    service = TranslationDictionaryService(db)
    items, total = await service.list_entries(
        source_lang=source_lang, target_lang=target_lang, search=search, limit=limit, offset=offset
    )
    return TranslationDictionaryPageOut(items=items, total=total)


@router.post("/translation/dictionary", response_model=TranslationDictionaryEntryOut, status_code=201)
async def create_dictionary_entry(
    payload: TranslationDictionaryEntryCreate, db: AsyncSession = Depends(get_db)
) -> TranslationDictionaryEntryOut:
    service = TranslationDictionaryService(db)
    try:
        return await service.create(**payload.model_dump())
    except TranslationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/translation/dictionary/{entry_id}", response_model=TranslationDictionaryEntryOut)
async def update_dictionary_entry(
    entry_id: int, payload: TranslationDictionaryEntryUpdate, db: AsyncSession = Depends(get_db)
) -> TranslationDictionaryEntryOut:
    service = TranslationDictionaryService(db)
    try:
        return await service.update(entry_id, **payload.model_dump(exclude_unset=True))
    except TranslationError as exc:
        status = 404 if "not found" in str(exc) else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.delete("/translation/dictionary/{entry_id}", status_code=204)
async def delete_dictionary_entry(entry_id: int, db: AsyncSession = Depends(get_db)) -> None:
    service = TranslationDictionaryService(db)
    try:
        await service.delete(entry_id)
    except TranslationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
