from __future__ import annotations

from ips_db import Term
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TermRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_existing(self, lemmas: set[str], language: str) -> dict[str, int]:
        """Lemma -> term_id for the subset of lemmas already indexed; unknown
        terms are simply absent."""
        if not lemmas:
            return {}
        result = await self._session.execute(
            select(Term).where(Term.language == language, Term.lemma.in_(lemmas))
        )
        return {term.lemma: term.id for term in result.scalars().all()}

    async def get_or_create_many(self, lemmas: set[str], language: str) -> dict[str, int]:
        """Lemma -> term_id for every lemma, creating rows for unseen ones."""
        if not lemmas:
            return {}
        result = await self._session.execute(
            select(Term).where(Term.language == language, Term.lemma.in_(lemmas))
        )
        term_ids = {term.lemma: term.id for term in result.scalars().all()}

        missing = lemmas - term_ids.keys()
        if missing:
            new_terms = [Term(lemma=lemma, language=language) for lemma in missing]
            self._session.add_all(new_terms)
            await self._session.flush()
            term_ids.update({term.lemma: term.id for term in new_terms})
        return term_ids
