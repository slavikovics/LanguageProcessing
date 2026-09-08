from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from nlp_core.content_extraction import extract_main_content
from nlp_core.tokenization import clean_html

from app.core.config import get_settings
from app.domain.indexing import chunk_text
from app.domain.lang_id import METHODS, IdentificationOutcome, LangIdError
from app.infrastructure.lang_id_client import LangIdServiceClient
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.lang_id import LangIdProfileRepository

from .profiles import load_lexical_profiles


class LangIdIdentificationService:

    def __init__(
        self,
        session: AsyncSession,
        *,
        nlp_client: NlpServiceClient | None = None,
        lang_id_client: LangIdServiceClient | None = None,
    ) -> None:
        self._documents = DocumentRepository(session)
        self._profiles = LangIdProfileRepository(session)
        self._nlp = nlp_client or NlpServiceClient()
        self._lang_id = lang_id_client or LangIdServiceClient()

    async def identify_text(
        self, text: str, methods: list[str] | None = None
    ) -> list[IdentificationOutcome]:
        outcomes: list[IdentificationOutcome] = []
        for method in methods or METHODS:
            if method == "frequent_words":
                profiles = await load_lexical_profiles(self._profiles, "frequent_words")
                if len(profiles) < 2:
                    continue
                result = await self._lang_id.identify_frequent_words(profiles, text)
            elif method == "alphabetic":
                profiles = await load_lexical_profiles(self._profiles, "alphabetic")
                if len(profiles) < 2:
                    continue
                result = await self._lang_id.identify_alphabetic(profiles, text)
            elif method == "neural":
                profile = await self._profiles.get("neural", None)
                if profile is None:
                    continue
                data = profile.profile_data
                representative_text = (chunk_text(text) or [""])[0]
                vector = (await self._nlp.embed_documents([representative_text]))[0]
                result = await self._lang_id.identify_neural(
                    data["weights"], data["bias"], data["classes"], vector
                )
            else:
                raise LangIdError(f"unknown method '{method}'")

            outcomes.append(
                IdentificationOutcome(
                    method=method,
                    predicted_language=result["predicted_language"],
                    distances=result["distances"],
                    elapsed_ms=result["elapsed_ms"],
                )
            )
        return outcomes

    async def identify_document(
        self, document_id: int, methods: list[str] | None = None
    ) -> list[IdentificationOutcome]:
        document = await self._documents.get(document_id)
        if document is None:
            raise LangIdError(f"document {document_id} not found")
        return await self.identify_text(document.clean_text, methods)

    async def identify_url(
        self, url: str, methods: list[str] | None = None
    ) -> list[IdentificationOutcome]:
        headers = {"User-Agent": get_settings().crawler_user_agent}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
        text = extract_main_content(response.text)
        return await self.identify_text(text, methods)

    async def identify_raw_html(
        self, html: str, methods: list[str] | None = None
    ) -> list[IdentificationOutcome]:
        return await self.identify_text(clean_html(html), methods)
