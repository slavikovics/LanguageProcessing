from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.collections import CollectionBusy, CollectionNotFound, CollectionService
from app.application.crawl_jobs import CrawlJobService
from app.core.database import get_db
from app.domain.crawl_jobs import InvalidCrawlJobConfig
from app.infrastructure.repositories import CollectionRepository
from app.interface.schemas import CollectionCreate, CollectionOut, CrawlJobOut

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionOut, status_code=201)
async def create_collection(
    payload: CollectionCreate, db: AsyncSession = Depends(get_db)
) -> CollectionOut:
    repo = CollectionRepository(db)
    collection = await repo.create(name=payload.name, language=payload.language)
    await db.commit()
    return CollectionOut(
        id=collection.id,
        name=collection.name,
        language=collection.language,
        created_at=collection.created_at,
        document_count=0,
        documents_changed_at=collection.documents_changed_at,
    )


@router.get("", response_model=list[CollectionOut])
async def list_collections(db: AsyncSession = Depends(get_db)) -> list[CollectionOut]:
    repo = CollectionRepository(db)
    rows = await repo.list_with_document_counts()
    return [
        CollectionOut(
            id=collection.id,
            name=collection.name,
            language=collection.language,
            created_at=collection.created_at,
            document_count=count,
            documents_changed_at=collection.documents_changed_at,
        )
        for collection, count in rows
    ]


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: int, db: AsyncSession = Depends(get_db)) -> None:
    service = CollectionService(db)
    try:
        await service.delete(collection_id)
    except CollectionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CollectionBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{collection_id}/refresh", response_model=CrawlJobOut, status_code=201)
async def refresh_collection(collection_id: int, db: AsyncSession = Depends(get_db)) -> CrawlJobOut:
    """Re-fetches every document in the collection that has a URL, updating
    each in place — tracked as an ordinary crawl_job (mode='refresh') so the
    existing progress UI/WS works unchanged."""
    service = CrawlJobService(db)
    try:
        return await service.create_refresh_job(collection_id)
    except InvalidCrawlJobConfig as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
