from __future__ import annotations

from ips_db import Document
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents import DocumentError, build_document_input
from app.infrastructure.repositories.collections import CollectionRepository
from app.infrastructure.repositories.documents import DocumentRepository

_DUPLICATE_URL_MESSAGE = "a document with this URL already exists in this collection"


class DocumentService:
    """Manual CRUD for documents — the same rows the crawler writes, just
    entered by hand. A create/update/delete leaves the collection's index
    stale until the user reindexes (same as after a crawl); this service
    does not trigger indexing itself, only marks the collection as changed
    (Collection.documents_changed_at) so the UI can flag that staleness.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._collections = CollectionRepository(session)

    async def create_document(
        self, collection_id: int, *, title: str, url: str | None, clean_text: str
    ) -> Document:
        collection = await self._collections.get(collection_id)
        if collection is None:
            raise DocumentError(f"collection {collection_id} not found")
        payload = build_document_input(title=title, url=url, clean_text=clean_text)
        try:
            document = await self._documents.create(
                collection_id=collection_id,
                title=payload.title,
                url=payload.url,
                clean_text=payload.clean_text,
                language=collection.language,
            )
            await self._collections.touch_documents_changed(collection_id)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DocumentError(_DUPLICATE_URL_MESSAGE) from exc
        return document

    async def update_document(
        self, document_id: int, *, title: str, url: str | None, clean_text: str
    ) -> Document:
        document = await self._documents.get(document_id)
        if document is None:
            raise DocumentError(f"document {document_id} not found")
        payload = build_document_input(title=title, url=url, clean_text=clean_text)
        try:
            await self._documents.update(
                document, title=payload.title, url=payload.url, clean_text=payload.clean_text
            )
            await self._collections.touch_documents_changed(document.collection_id)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DocumentError(_DUPLICATE_URL_MESSAGE) from exc
        return document

    async def delete_document(self, document_id: int) -> None:
        document = await self._documents.get(document_id)
        if document is None:
            raise DocumentError(f"document {document_id} not found")
        collection_id = document.collection_id
        await self._documents.delete(document)
        await self._collections.touch_documents_changed(collection_id)
        await self._session.commit()
