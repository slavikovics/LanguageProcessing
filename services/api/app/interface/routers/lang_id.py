import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.lang_id import (
    LangIdIdentificationService,
    LangIdLabelingService,
    LangIdProfileService,
    LangIdTestRunService,
    LangIdTrainingService,
)
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.domain.lang_id import LangIdError
from app.infrastructure.repositories.documents import DocumentRepository
from app.interface.schemas import (
    AutoSplitResultOut,
    BuildLexicalProfileRequest,
    DocumentOut,
    IdentificationOutcomeOut,
    IdentifyDocumentRequest,
    IdentifyResponseOut,
    IdentifyTextRequest,
    IdentifyUrlRequest,
    LabelProgressOut,
    LangIdCompareResponseOut,
    LangIdProfileOut,
    LangIdResultOut,
    LangIdRunCreate,
    LangIdRunOut,
    LangIdRunSummaryOut,
    LangIdTrainingJobOut,
    LanguageLabelIn,
)

router = APIRouter(tags=["lang-id"])

_TERMINAL_JOB_STATUSES = {"completed", "failed"}


def _raise_for_lang_id_error(exc: LangIdError) -> None:
    status = 404 if "not found" in str(exc) else 422
    raise HTTPException(status_code=status, detail=str(exc)) from exc


async def _run_training_job(job_id: int) -> None:
    async with SessionLocal() as session:
        await LangIdTrainingService(session).run_neural_training(job_id)


async def _run_lang_id_run(run_id: int) -> None:
    async with SessionLocal() as session:
        await LangIdTestRunService(session).run_job(run_id)


# -- labeling ----------------------------------------------------------


@router.get("/collections/{collection_id}/lang-id/unlabeled-documents", response_model=list[DocumentOut])
async def list_unlabeled_documents(
    collection_id: int, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)
) -> list[DocumentOut]:
    repo = DocumentRepository(db)
    return await repo.list_unlabeled_by_collection(collection_id, limit=limit, offset=offset)


@router.get("/collections/{collection_id}/lang-id/label-progress", response_model=LabelProgressOut)
async def get_label_progress(collection_id: int, db: AsyncSession = Depends(get_db)) -> LabelProgressOut:
    service = LangIdLabelingService(db)
    return LabelProgressOut(**await service.get_label_progress(collection_id))


@router.post("/collections/{collection_id}/lang-id/auto-split", response_model=AutoSplitResultOut)
async def auto_split_train_test(
    collection_id: int, test_ratio: float = 0.2, db: AsyncSession = Depends(get_db)
) -> AutoSplitResultOut:
    service = LangIdLabelingService(db)
    try:
        result = await service.auto_split(collection_id, test_ratio=test_ratio)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)
    return AutoSplitResultOut(**result)


@router.put("/documents/{document_id}/language-label", response_model=DocumentOut)
async def set_language_label(
    document_id: int, payload: LanguageLabelIn, db: AsyncSession = Depends(get_db)
) -> DocumentOut:
    service = LangIdLabelingService(db)
    try:
        return await service.set_language_label(
            document_id, confirmed_language=payload.confirmed_language, corpus_split=payload.corpus_split
        )
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)


# -- profiles ------------------------------------------------------------


@router.get("/lang-id/profiles", response_model=list[LangIdProfileOut])
async def list_profiles(db: AsyncSession = Depends(get_db)) -> list[LangIdProfileOut]:
    service = LangIdProfileService(db)
    return await service.list_profiles()


@router.post("/lang-id/profiles/frequent-words", response_model=LangIdProfileOut, status_code=201)
async def build_frequent_words_profile(
    payload: BuildLexicalProfileRequest, db: AsyncSession = Depends(get_db)
) -> LangIdProfileOut:
    service = LangIdProfileService(db)
    try:
        return await service.build_lexical_profile("frequent_words", payload.language)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)


@router.post("/lang-id/profiles/alphabetic", response_model=LangIdProfileOut, status_code=201)
async def build_alphabetic_profile(
    payload: BuildLexicalProfileRequest, db: AsyncSession = Depends(get_db)
) -> LangIdProfileOut:
    service = LangIdProfileService(db)
    try:
        return await service.build_lexical_profile("alphabetic", payload.language)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)


# -- neural training, with live progress ---------------------------------


@router.post("/lang-id/neural/train", response_model=LangIdTrainingJobOut, status_code=201)
async def start_neural_training(
    background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> LangIdTrainingJobOut:
    service = LangIdTrainingService(db)
    try:
        job = await service.start_neural_training()
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)
    background_tasks.add_task(_run_training_job, job.id)
    return job


@router.get("/lang-id/neural/train/{job_id}", response_model=LangIdTrainingJobOut)
async def get_neural_training_job(job_id: int, db: AsyncSession = Depends(get_db)) -> LangIdTrainingJobOut:
    service = LangIdTrainingService(db)
    job = await service.get_training_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="training job not found")
    return job


@router.get("/lang-id/neural/train/latest", response_model=LangIdTrainingJobOut | None)
async def get_latest_neural_training_job(db: AsyncSession = Depends(get_db)) -> LangIdTrainingJobOut | None:
    service = LangIdTrainingService(db)
    return await service.get_latest_training_job()


@router.websocket("/lang-id/neural/train/ws/{job_id}")
async def neural_training_progress_ws(websocket: WebSocket, job_id: int) -> None:
    """Same polling-and-push shape as /index-jobs/ws/{job_id} — the frontend
    falls back to plain GET polling if this connection drops."""
    await websocket.accept()
    settings = get_settings()
    last_payload: str | None = None
    try:
        while True:
            async with SessionLocal() as session:
                service = LangIdTrainingService(session)
                job = await service.get_training_job(job_id)
                if job is None:
                    await websocket.send_json({"error": "training job not found"})
                    break
                payload_model = LangIdTrainingJobOut.model_validate(job)

            payload = payload_model.model_dump_json()
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

            if payload_model.status in _TERMINAL_JOB_STATUSES:
                break
            await asyncio.sleep(settings.crawl_progress_poll_interval_seconds)
    except WebSocketDisconnect:
        pass


# -- identification --------------------------------------------------------


@router.post("/lang-id/identify", response_model=IdentifyResponseOut)
async def identify_document(
    payload: IdentifyDocumentRequest, db: AsyncSession = Depends(get_db)
) -> IdentifyResponseOut:
    service = LangIdIdentificationService(db)
    try:
        outcomes = await service.identify_document(payload.document_id, payload.methods)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)
    return IdentifyResponseOut(results=[IdentificationOutcomeOut(**vars(o)) for o in outcomes])


@router.post("/lang-id/identify-url", response_model=IdentifyResponseOut)
async def identify_url(payload: IdentifyUrlRequest, db: AsyncSession = Depends(get_db)) -> IdentifyResponseOut:
    service = LangIdIdentificationService(db)
    try:
        outcomes = await service.identify_url(payload.url, payload.methods)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)
    except Exception as exc:  # noqa: BLE001 - surfaces fetch/parsing failures to the UI
        raise HTTPException(status_code=422, detail=f"could not fetch/classify URL: {exc}") from exc
    return IdentifyResponseOut(results=[IdentificationOutcomeOut(**vars(o)) for o in outcomes])


@router.post("/lang-id/identify-text", response_model=IdentifyResponseOut)
async def identify_text(
    payload: IdentifyTextRequest, db: AsyncSession = Depends(get_db)
) -> IdentifyResponseOut:
    service = LangIdIdentificationService(db)
    try:
        if payload.is_html:
            outcomes = await service.identify_raw_html(payload.text, payload.methods)
        else:
            outcomes = await service.identify_text(payload.text, payload.methods)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)
    return IdentifyResponseOut(results=[IdentificationOutcomeOut(**vars(o)) for o in outcomes])


# -- test-collection runs ----------------------------------------------


@router.post("/lang-id/runs", response_model=list[LangIdRunOut], status_code=201)
async def create_runs(
    payload: LangIdRunCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
) -> list[LangIdRunOut]:
    service = LangIdTestRunService(db)
    try:
        runs = await service.start_run(payload.collection_id, payload.methods)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)
    for run in runs:
        background_tasks.add_task(_run_lang_id_run, run.id)
    return runs


@router.get("/lang-id/runs/{run_id}", response_model=LangIdRunOut)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)) -> LangIdRunOut:
    service = LangIdTestRunService(db)
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="lang-id run not found")
    return run


@router.get("/collections/{collection_id}/lang-id/runs", response_model=list[LangIdRunOut])
async def list_runs_by_collection(collection_id: int, db: AsyncSession = Depends(get_db)) -> list[LangIdRunOut]:
    service = LangIdTestRunService(db)
    return await service.list_runs_by_collection(collection_id)


@router.websocket("/lang-id/runs/ws/{run_id}")
async def lang_id_run_progress_ws(websocket: WebSocket, run_id: int) -> None:
    await websocket.accept()
    settings = get_settings()
    last_payload: str | None = None
    try:
        while True:
            async with SessionLocal() as session:
                service = LangIdTestRunService(session)
                run = await service.get_run(run_id)
                if run is None:
                    await websocket.send_json({"error": "lang-id run not found"})
                    break
                payload_model = LangIdRunOut.model_validate(run)

            payload = payload_model.model_dump_json()
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

            if payload_model.status in _TERMINAL_JOB_STATUSES:
                break
            await asyncio.sleep(settings.crawl_progress_poll_interval_seconds)
    except WebSocketDisconnect:
        pass


@router.get("/lang-id/runs/{run_id}/results", response_model=list[LangIdResultOut])
async def get_run_results(run_id: int, db: AsyncSession = Depends(get_db)) -> list[LangIdResultOut]:
    service = LangIdTestRunService(db)
    return await service.get_run_results(run_id)


@router.get("/lang-id/runs/{run_id}/summary", response_model=LangIdRunSummaryOut)
async def get_run_summary(run_id: int, db: AsyncSession = Depends(get_db)) -> LangIdRunSummaryOut:
    service = LangIdTestRunService(db)
    try:
        return await service.get_run_summary(run_id)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)


@router.get("/lang-id/compare", response_model=LangIdCompareResponseOut)
async def compare(
    collection_id: int, methods: str = "frequent_words,alphabetic,neural", db: AsyncSession = Depends(get_db)
) -> LangIdCompareResponseOut:
    service = LangIdTestRunService(db)
    method_list = [m for m in methods.split(",") if m]
    summaries = await service.compare(collection_id, method_list)
    return {"summaries": summaries}


@router.post("/lang-id/rerun", response_model=LangIdCompareResponseOut)
async def rerun(payload: LangIdRunCreate, db: AsyncSession = Depends(get_db)) -> LangIdCompareResponseOut:
    """Like GET /lang-id/compare, but runs fresh classification passes for
    every requested method first — the classification-quality analogue of
    POST /collections/{id}/metrics/rerun."""
    service = LangIdTestRunService(db)
    try:
        summaries = await service.rerun_and_compare(payload.collection_id, payload.methods)
    except LangIdError as exc:
        _raise_for_lang_id_error(exc)
    return {"summaries": summaries}
