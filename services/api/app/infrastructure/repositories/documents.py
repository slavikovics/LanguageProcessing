from __future__ import annotations

from ips_db import Document
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_collection(self, collection_id: int, *, limit: int = 50, offset: int = 0) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.collection_id == collection_id)
            .order_by(Document.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get(self, document_id: int) -> Document | None:
        return await self._session.get(Document, document_id)

    async def count_by_collection(self, collection_id: int) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Document).where(Document.collection_id == collection_id)
        )
        return int(result.scalar_one())

    async def list_all_by_collection(self, collection_id: int) -> list[Document]:
        result = await self._session.execute(
            select(Document).where(Document.collection_id == collection_id).order_by(Document.id)
        )
        return list(result.scalars().all())

    async def list_by_ids(self, document_ids: list[int]) -> list[Document]:
        if not document_ids:
            return []
        result = await self._session.execute(select(Document).where(Document.id.in_(document_ids)))
        return list(result.scalars().all())

    async def list_ids_by_collection(self, collection_id: int) -> list[int]:
        result = await self._session.execute(
            select(Document.id).where(Document.collection_id == collection_id)
        )
        return [row[0] for row in result.all()]

    async def create(
        self, *, collection_id: int, title: str, url: str | None, clean_text: str, language: str
    ) -> Document:
        document = Document(
            collection_id=collection_id,
            title=title,
            url=url,
            clean_text=clean_text,
            language=language,
            char_count=len(clean_text),
        )
        self._session.add(document)
        await self._session.flush()
        return document

    async def update(
        self, document: Document, *, title: str, url: str | None, clean_text: str
    ) -> Document:
        document.title = title
        document.url = url
        document.clean_text = clean_text
        document.char_count = len(clean_text)
        await self._session.flush()
        return document

    async def delete(self, document: Document) -> None:
        await self._session.delete(document)

    async def get_by_url(self, collection_id: int, url: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.collection_id == collection_id, Document.url == url)
        )
        return result.scalars().first()

    async def list_urls_by_collection(self, collection_id: int) -> list[str]:
        result = await self._session.execute(
            select(Document.url).where(
                Document.collection_id == collection_id, Document.url.is_not(None)
            )
        )
        return [row[0] for row in result.all()]

    async def delete_all_by_collection(self, collection_id: int) -> None:
        """Bulk-deletes every document in the collection; ON DELETE CASCADE
        clears the built index and any qrels/results pointing at them."""
        await self._session.execute(delete(Document).where(Document.collection_id == collection_id))

    # -- LR2 language labeling / train-test split ---------------------------

    async def list_unlabeled_by_collection(
        self, collection_id: int, *, limit: int = 50, offset: int = 0
    ) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.collection_id == collection_id, Document.confirmed_language.is_(None))
            .order_by(Document.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_unlabeled_by_collection(self, collection_id: int) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.collection_id == collection_id, Document.confirmed_language.is_(None))
        )
        return int(result.scalar_one())

    async def count_labeled_by_collection(self, collection_id: int) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Document)
            .where(
                Document.collection_id == collection_id, Document.confirmed_language.is_not(None)
            )
        )
        return int(result.scalar_one())

    async def count_by_collection_and_split(self, collection_id: int, split: str) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.collection_id == collection_id, Document.corpus_split == split)
        )
        return int(result.scalar_one())

    async def set_language_label(
        self, document: Document, *, confirmed_language: str | None, corpus_split: str | None
    ) -> Document:
        document.confirmed_language = confirmed_language
        document.corpus_split = corpus_split
        await self._session.flush()
        return document

    async def list_distinct_training_languages(self) -> list[str]:
        result = await self._session.execute(
            select(Document.confirmed_language)
            .where(Document.corpus_split == "train", Document.confirmed_language.is_not(None))
            .distinct()
        )
        return [row[0] for row in result.all()]

    async def count_confirmed(self, language: str) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.confirmed_language == language)
        )
        return int(result.scalar_one())

    async def list_training_documents(self, language: str) -> list[Document]:
        """Every document across ANY collection confirmed as `language` and
        assigned to the training split — LR2 profiles are built from this,
        independent of which collection a document was crawled into."""
        result = await self._session.execute(
            select(Document).where(
                Document.confirmed_language == language, Document.corpus_split == "train"
            )
        )
        return list(result.scalars().all())

    async def list_confirmed_without_split(self, collection_id: int) -> list[Document]:
        """Documents with a confirmed language but no train/test assignment
        yet — what the "auto-split" action fills in, without touching
        documents someone already split by hand."""
        result = await self._session.execute(
            select(Document).where(
                Document.collection_id == collection_id,
                Document.confirmed_language.is_not(None),
                Document.corpus_split.is_(None),
            )
        )
        return list(result.scalars().all())

    async def bulk_set_corpus_split(self, *, train_ids: list[int], test_ids: list[int]) -> None:
        if train_ids:
            await self._session.execute(
                update(Document).where(Document.id.in_(train_ids)).values(corpus_split="train")
            )
        if test_ids:
            await self._session.execute(
                update(Document).where(Document.id.in_(test_ids)).values(corpus_split="test")
            )

    async def list_test_documents(self, collection_id: int) -> list[Document]:
        """Test documents are collection-scoped (unlike training), so a run
        can target a collection different from the one profiles were built
        from, to check cross-domain generalization."""
        result = await self._session.execute(
            select(Document).where(
                Document.collection_id == collection_id,
                Document.confirmed_language.is_not(None),
                Document.corpus_split == "test",
            )
        )
        return list(result.scalars().all())
