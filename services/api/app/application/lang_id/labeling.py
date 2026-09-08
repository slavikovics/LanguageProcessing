from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lang_id import LangIdError, split_train_test
from app.infrastructure.repositories.documents import DocumentRepository


class LangIdLabelingService:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentRepository(session)

    async def set_language_label(
        self, document_id: int, *, confirmed_language: str | None, corpus_split: str | None
    ):
        document = await self._documents.get(document_id)
        if document is None:
            raise LangIdError(f"document {document_id} not found")
        updated = await self._documents.set_language_label(
            document, confirmed_language=confirmed_language, corpus_split=corpus_split
        )
        await self._session.commit()
        return updated

    async def auto_split(self, collection_id: int, *, test_ratio: float = 0.2) -> dict[str, int]:
        documents = await self._documents.list_confirmed_without_split(collection_id)
        if not documents:
            raise LangIdError(
                "нет размеченных документов без выборки — подтвердите язык хотя бы у одного "
                "документа, прежде чем разбивать автоматически"
            )
        by_language: dict[str, list[int]] = {}
        for document in documents:
            by_language.setdefault(document.confirmed_language, []).append(document.id)

        train_ids, test_ids = split_train_test(by_language, test_ratio=test_ratio)
        await self._documents.bulk_set_corpus_split(train_ids=train_ids, test_ids=test_ids)
        await self._session.commit()
        return {"train_assigned": len(train_ids), "test_assigned": len(test_ids)}

    async def get_label_progress(self, collection_id: int) -> dict[str, int]:
        total = await self._documents.count_by_collection(collection_id)
        unlabeled = await self._documents.count_unlabeled_by_collection(collection_id)
        train_count = await self._documents.count_by_collection_and_split(collection_id, "train")
        test_count = await self._documents.count_by_collection_and_split(collection_id, "test")
        return {
            "total": total,
            "labeled": total - unlabeled,
            "unlabeled": unlabeled,
            "train_count": train_count,
            "test_count": test_count,
        }
