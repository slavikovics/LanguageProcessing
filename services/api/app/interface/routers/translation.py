from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.translation import TranslationDictionaryService, TranslationService
from app.core.database import get_db
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
    TranslationRunWordOut,
)

router = APIRouter(tags=["translation"])


def _raise_for_translation_error(exc: TranslationError) -> None:
    status = 404 if "not found" in str(exc) else 422
    raise HTTPException(status_code=status, detail=str(exc)) from exc


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
        )
    except TranslationError as exc:
        _raise_for_translation_error(exc)


@router.get(
    "/translation/collections/{collection_id}/runs/latest",
    response_model=TranslationRunOut | None,
)
async def get_latest_translation_run_for_collection(
    collection_id: int, db: AsyncSession = Depends(get_db)
) -> TranslationRunOut | None:
    service = TranslationService(db)
    return await service.get_latest_for_collection(collection_id)


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
