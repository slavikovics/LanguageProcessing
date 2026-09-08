from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.crawl_jobs import CrawlJobService
from app.application.crawl_seeds import CrawlSeedNotFound, CrawlSeedService
from app.core.database import get_db
from app.domain.crawl_jobs import InvalidCrawlJobConfig
from app.interface.schemas import CrawlJobOut, CrawlSeedCreate, CrawlSeedOut, CrawlSeedUpdate

router = APIRouter(tags=["crawl-seeds"])


@router.get("/collections/{collection_id}/crawl-seeds", response_model=list[CrawlSeedOut])
async def list_crawl_seeds(collection_id: int, db: AsyncSession = Depends(get_db)) -> list[CrawlSeedOut]:
    service = CrawlSeedService(db)
    return await service.list_seeds(collection_id)


@router.post("/collections/{collection_id}/crawl-seeds", response_model=CrawlSeedOut, status_code=201)
async def create_crawl_seed(
    collection_id: int, payload: CrawlSeedCreate, db: AsyncSession = Depends(get_db)
) -> CrawlSeedOut:
    service = CrawlSeedService(db)
    try:
        return await service.create_seed(
            collection_id,
            url=payload.url,
            max_documents=payload.max_documents,
            max_depth=payload.max_depth,
            same_domain_only=payload.same_domain_only,
            language=payload.language,
        )
    except InvalidCrawlJobConfig as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/crawl-seeds/{seed_id}", response_model=CrawlSeedOut)
async def update_crawl_seed(
    seed_id: int, payload: CrawlSeedUpdate, db: AsyncSession = Depends(get_db)
) -> CrawlSeedOut:
    service = CrawlSeedService(db)
    try:
        return await service.update_seed(
            seed_id,
            url=payload.url,
            max_documents=payload.max_documents,
            max_depth=payload.max_depth,
            same_domain_only=payload.same_domain_only,
            language=payload.language,
        )
    except CrawlSeedNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidCrawlJobConfig as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/crawl-seeds/{seed_id}", status_code=204)
async def delete_crawl_seed(seed_id: int, db: AsyncSession = Depends(get_db)) -> None:
    service = CrawlSeedService(db)
    try:
        await service.delete_seed(seed_id)
    except CrawlSeedNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/collections/{collection_id}/crawl-seeds/run",
    response_model=list[CrawlJobOut],
    status_code=201,
)
async def run_collection_crawl(collection_id: int, db: AsyncSession = Depends(get_db)) -> list[CrawlJobOut]:
    service = CrawlJobService(db)
    try:
        return await service.run_collection_crawl(collection_id)
    except InvalidCrawlJobConfig as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
