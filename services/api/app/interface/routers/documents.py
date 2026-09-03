from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.repositories import DocumentRepository
from app.interface.schemas import DocumentOut

router = APIRouter(tags=["documents"])


@router.get("/collections/{collection_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    collection_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    repo = DocumentRepository(db)
    return await repo.list_by_collection(collection_id, limit=limit, offset=offset)


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)) -> DocumentOut:
    repo = DocumentRepository(db)
    document = await repo.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return document
