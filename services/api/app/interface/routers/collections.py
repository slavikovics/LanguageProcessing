from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.repositories import CollectionRepository
from app.interface.schemas import CollectionCreate, CollectionOut

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionOut, status_code=201)
async def create_collection(
    payload: CollectionCreate, db: AsyncSession = Depends(get_db)
) -> CollectionOut:
    repo = CollectionRepository(db)
    collection = await repo.create(name=payload.name, language=payload.language)
    await db.commit()
    return collection


@router.get("", response_model=list[CollectionOut])
async def list_collections(db: AsyncSession = Depends(get_db)) -> list[CollectionOut]:
    repo = CollectionRepository(db)
    return await repo.list()
