from __future__ import annotations

from ips_db import Term
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# asyncpg caps a single query at 32767 bind parameters. A big multi-language
# collection's corpus vocabulary can itself exceed that count, so a single
# `Term.lemma.in_(lemmas)` query needs to be split into chunks comfortably
# under the limit (leaving headroom for the `language` parameter too).
_IN_CLAUSE_CHUNK_SIZE = 10_000


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class TermRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_existing(self, lemmas: set[str], language: str) -> dict[str, int]:
        """Lemma -> term_id for the subset of lemmas already indexed; unknown
        terms are simply absent."""
        if not lemmas:
            return {}
        term_ids: dict[str, int] = {}
        for chunk in _chunked(list(lemmas), _IN_CLAUSE_CHUNK_SIZE):
            result = await self._session.execute(
                select(Term).where(Term.language == language, Term.lemma.in_(chunk))
            )
            term_ids.update({term.lemma: term.id for term in result.scalars().all()})
        return term_ids

    async def get_or_create_many(self, lemmas: set[str], language: str) -> dict[str, int]:
        """Lemma -> term_id for every lemma, creating rows for unseen ones."""
        if not lemmas:
            return {}
        term_ids = await self.get_existing(lemmas, language)

        missing = lemmas - term_ids.keys()
        if missing:
            new_terms = [Term(lemma=lemma, language=language) for lemma in missing]
            self._session.add_all(new_terms)
            await self._session.flush()
            term_ids.update({term.lemma: term.id for term in new_terms})
        return term_ids
