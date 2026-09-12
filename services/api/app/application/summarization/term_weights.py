from __future__ import annotations

from nlp_core.weighting import modified_term_weight
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.summarization import DocumentTermStatsRepository


async def compute_modified_term_weights(
    session: AsyncSession, *, document_id: int, collection_id: int
) -> dict[str, float]:
    """w(t,D) per LR3's modified TF-IDF formula, scoped to the document's collection."""
    term_stats = DocumentTermStatsRepository(session)
    documents = DocumentRepository(session)

    term_frequencies = await term_stats.get_term_frequencies(document_id)
    if not term_frequencies:
        return {}

    tf_max = max(term_frequencies.values())
    total_documents = max(await documents.count_by_collection(collection_id), 1)
    document_frequencies = await term_stats.get_document_frequencies(
        collection_id, set(term_frequencies)
    )

    return {
        lemma: modified_term_weight(
            tf=tf,
            tf_max=tf_max,
            document_frequency=document_frequencies.get(lemma, 1),
            total_documents=total_documents,
        )
        for lemma, tf in term_frequencies.items()
    }
