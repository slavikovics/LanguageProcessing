from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.repositories import SearchModelRepository
from app.interface.schemas import SearchModelOut

router = APIRouter(tags=["search-models"])


@router.get("/search-models", response_model=list[SearchModelOut])
async def list_search_models(db: AsyncSession = Depends(get_db)) -> list[SearchModelOut]:
    return await SearchModelRepository(db).list_active()
