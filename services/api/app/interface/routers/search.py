from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.search import SearchService
from app.core.database import get_db
from app.domain.search import SearchError
from app.interface.schemas import SearchRequest, SearchResponseOut

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponseOut)
async def search(payload: SearchRequest, db: AsyncSession = Depends(get_db)) -> SearchResponseOut:
    service = SearchService(db)
    try:
        return await service.search(
            collection_id=payload.collection_id,
            text=payload.text,
            top_k=payload.top_k,
            model=payload.model,
        )
    except SearchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
