from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.documents import DocumentService
from app.core.database import get_db
from app.domain.documents import DocumentError
from app.infrastructure.repositories.documents import DocumentRepository
from app.interface.schemas import DocumentCreate, DocumentDetailOut, DocumentOut, DocumentUpdate

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


@router.post("/collections/{collection_id}/documents", response_model=DocumentDetailOut, status_code=201)
async def create_document(
    collection_id: int, payload: DocumentCreate, db: AsyncSession = Depends(get_db)
) -> DocumentDetailOut:
    service = DocumentService(db)
    try:
        return await service.create_document(
            collection_id, title=payload.title, url=payload.url, clean_text=payload.clean_text
        )
    except DocumentError as exc:
        status = 404 if "not found" in str(exc) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/documents/{document_id}", response_model=DocumentDetailOut)
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)) -> DocumentDetailOut:
    repo = DocumentRepository(db)
    document = await repo.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return document


@router.put("/documents/{document_id}", response_model=DocumentDetailOut)
async def update_document(
    document_id: int, payload: DocumentUpdate, db: AsyncSession = Depends(get_db)
) -> DocumentDetailOut:
    service = DocumentService(db)
    try:
        return await service.update_document(
            document_id, title=payload.title, url=payload.url, clean_text=payload.clean_text
        )
    except DocumentError as exc:
        status = 404 if "not found" in str(exc) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db)) -> None:
    service = DocumentService(db)
    try:
        await service.delete_document(document_id)
    except DocumentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
