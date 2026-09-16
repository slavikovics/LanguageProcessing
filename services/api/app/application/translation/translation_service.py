from __future__ import annotations

import time

from ips_db import TranslationRun, TranslationRunWord
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.translation import (
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    TranslationError,
)
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.translation import (
    TranslationDictionaryRepository,
    TranslationRunRepository,
    TranslationRunWordRepository,
)


class TranslationService:
    def __init__(self, session: AsyncSession, *, nlp_client: NlpServiceClient | None = None) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._dictionary = TranslationDictionaryRepository(session)
        self._runs = TranslationRunRepository(session)
        self._run_words = TranslationRunWordRepository(session)
        self._nlp = nlp_client or NlpServiceClient()

    async def translate(
        self,
        *,
        document_id: int | None,
        text: str | None,
        collection_id: int | None = None,
        source_lang: str = DEFAULT_SOURCE_LANGUAGE,
        target_lang: str = DEFAULT_TARGET_LANGUAGE,
        test_run_id: int | None = None,
        lookup_override: dict[str, str] | None = None,
    ) -> TranslationRun:
        if document_id is not None:
            document = await self._documents.get(document_id)
            if document is None:
                raise TranslationError(f"document {document_id} not found")
            source_text = document.clean_text
            collection_id = document.collection_id
        elif text and text.strip():
            source_text = text
        else:
            raise TranslationError("either document_id or non-empty text must be provided")

        lookup = (
            lookup_override
            if lookup_override is not None
            else await self._dictionary.as_lookup(source_lang=source_lang, target_lang=target_lang)
        )

        started = time.perf_counter()
        result = await self._nlp.translate(source_text, lookup)
        elapsed_ms = (time.perf_counter() - started) * 1000

        run = await self._runs.create(
            document_id=document_id,
            collection_id=collection_id,
            test_run_id=test_run_id,
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=source_text,
            translated_text=result["translated_text"],
            word_count=result["word_count"],
            translated_word_count=result["translated_word_count"],
            translated_text_word_count=len(result["translated_text"].split()),
            elapsed_ms=elapsed_ms,
        )
        await self._run_words.bulk_create(run.id, result["words"])
        await self._session.commit()
        return run

    async def get_run(self, run_id: int) -> TranslationRun | None:
        return await self._runs.get(run_id)

    async def list_runs(self, *, limit: int = 20) -> list[TranslationRun]:
        return await self._runs.list_recent(limit=limit)

    async def get_latest_for_collection(self, collection_id: int) -> TranslationRun | None:
        return await self._runs.get_latest_for_collection(collection_id)

    async def get_run_words(self, run_id: int) -> list[TranslationRunWord]:
        run = await self._runs.get(run_id)
        if run is None:
            raise TranslationError(f"translation run {run_id} not found")
        return await self._run_words.list_for_run(run_id)

    async def list_sentences(self, run_id: int) -> list[str]:
        run = await self._runs.get(run_id)
        if run is None:
            raise TranslationError(f"translation run {run_id} not found")
        return await self._nlp.split_sentences(run.source_text)

    async def parse_sentence(self, text: str) -> list[dict]:
        if not text.strip():
            raise TranslationError("sentence text must not be empty")
        return await self._nlp.parse_sentence(text)
