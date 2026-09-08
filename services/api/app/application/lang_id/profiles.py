from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lang_id import LangIdError
from app.infrastructure.lang_id_client import LangIdServiceClient
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.lang_id import LangIdProfileRepository

_PROFILE_DATA_KEY = {"frequent_words": "top_words", "alphabetic": "frequencies"}


async def load_lexical_profiles(profiles: LangIdProfileRepository, method: str) -> dict:
    key = _PROFILE_DATA_KEY[method]
    rows = await profiles.list_by_method(method)
    return {row.language: row.profile_data[key] for row in rows if row.language is not None}


class LangIdProfileService:

    def __init__(self, session: AsyncSession, *, lang_id_client: LangIdServiceClient | None = None) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._profiles = LangIdProfileRepository(session)
        self._lang_id = lang_id_client or LangIdServiceClient()

    async def list_profiles(self):
        return await self._profiles.list_all()

    async def build_lexical_profile(self, method: str, language: str):
        if method not in ("frequent_words", "alphabetic"):
            raise LangIdError(f"'{method}' is not a lexical profile method")
        documents = await self._documents.list_training_documents(language)
        if not documents:
            confirmed_count = await self._documents.count_confirmed(language)
            if confirmed_count == 0:
                raise LangIdError(
                    f"no documents are confirmed as '{language}' yet — label some in the "
                    "Разметка tab before building this profile"
                )
            raise LangIdError(
                f"{confirmed_count} document(s) are confirmed as '{language}', but none are "
                "assigned to the training split — set corpus_split='train' for at least one "
                "via the label editor"
            )
        texts = [document.clean_text for document in documents]

        if method == "frequent_words":
            top_words = await self._lang_id.build_frequent_words_profile(texts)
            profile_data = {"top_words": top_words}
        else:
            frequencies = await self._lang_id.build_alphabetic_profile(texts)
            profile_data = {"frequencies": frequencies}

        profile = await self._profiles.upsert(
            method=method,
            language=language,
            profile_data=profile_data,
            source_document_count=len(documents),
            source_char_count=sum(len(text) for text in texts),
        )
        await self._session.commit()
        return profile
