from __future__ import annotations

import time

from ips_db import DocumentSummary
from nlp_core.summarization import KeywordGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.summarization import METHODS, SelectedSentence, SummarizationError, SummaryOutcome
from app.infrastructure.nlp_client import NlpServiceClient
from app.infrastructure.repositories.documents import DocumentRepository
from app.infrastructure.repositories.summarization import (
    DocumentSummaryPolishRepository,
    DocumentSummaryRepository,
)
from app.infrastructure.summarization_client import SummarizationServiceClient

from .term_weights import compute_modified_term_weights

DEFAULT_KEYWORD_COUNT = None
"""`None` = full vocabulary, no cap on the number of keyword-hierarchy roots."""


class DocumentSummarizationService:

    def __init__(
        self,
        session: AsyncSession,
        *,
        nlp_client: NlpServiceClient | None = None,
        summarization_client: SummarizationServiceClient | None = None,
    ) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._summaries = DocumentSummaryRepository(session)
        self._polishes = DocumentSummaryPolishRepository(session)
        self._nlp = nlp_client or NlpServiceClient()
        self._summarization = summarization_client or SummarizationServiceClient()

    async def summarize_document(
        self, document_id: int, *, methods: list[str] | None = None, sentence_count: int = 10
    ) -> tuple[list[KeywordGroup], list[SummaryOutcome]]:
        document = await self._documents.get(document_id)
        if document is None:
            raise SummarizationError(f"document {document_id} not found")

        requested_methods = methods or list(METHODS)
        unknown = set(requested_methods) - set(METHODS)
        if unknown:
            raise SummarizationError(f"unknown summarization method(s): {sorted(unknown)}")

        term_weights = await compute_modified_term_weights(
            self._session, document_id=document_id, collection_id=document.collection_id
        )
        if not term_weights:
            raise SummarizationError(
                "document has no indexed terms yet — run indexing for this collection first"
            )
        keyword_groups = await self._summarization.extract_keyword_hierarchy(
            document.clean_text, term_weights, top_n=DEFAULT_KEYWORD_COUNT
        )
        keywords = [KeywordGroup(term=g["term"], children=g["children"]) for g in keyword_groups]

        outcomes: list[SummaryOutcome] = []
        for method in requested_methods:
            outcome = await self.run_method(method, document.clean_text, term_weights, sentence_count)
            outcomes.append(outcome)
            await self._summaries.create(
                run_id=None,
                document_id=document_id,
                method=method,
                sentence_count=sentence_count,
                summary_text=outcome.summary_text,
                summary_sentence_indices=[s.index for s in outcome.sentences],
                total_sentences=outcome.total_sentences,
                total_chars=outcome.document_chars,
                elapsed_ms=outcome.elapsed_ms,
            )
        await self._session.commit()
        return keywords, outcomes

    async def run_method(
        self, method: str, text: str, term_weights: dict[str, float], sentence_count: int
    ) -> SummaryOutcome:
        if method == "algorithmic":
            body = await self._summarization.summarize_algorithmic(text, term_weights, sentence_count)
        elif method == "textrank":
            body = await self._summarization.summarize_textrank(text, sentence_count)
        elif method == "embeddings":
            body = await self._run_embeddings_method(text, sentence_count)
        else:
            raise SummarizationError(f"unknown summarization method: {method}")

        sentences = [SelectedSentence(**sentence) for sentence in body["selected"]]
        return SummaryOutcome(
            method=method,
            sentences=sentences,
            total_sentences=body["total_sentences"],
            elapsed_ms=body["elapsed_ms"],
            document_chars=len(text),
        )

    async def _run_embeddings_method(self, text: str, sentence_count: int) -> dict:
        sentences = await self._nlp.split_sentences(text)
        if not sentences:
            return {"selected": [], "total_sentences": 0, "elapsed_ms": 0.0}
        started = time.perf_counter()
        vectors = await self._nlp.embed_documents(sentences)
        embed_elapsed_ms = (time.perf_counter() - started) * 1000
        body = await self._summarization.summarize_embeddings(sentences, vectors, sentence_count)
        body["elapsed_ms"] = body["elapsed_ms"] + embed_elapsed_ms
        return body

    async def list_summaries(self, document_id: int) -> list[DocumentSummary]:
        return await self._summaries.list_for_document(document_id)

    async def polish_summary(self, summary_id: int, *, language: str | None = None) -> tuple[str, str]:
        summary = await self._summaries.get(summary_id)
        if summary is None:
            raise SummarizationError(f"summary {summary_id} not found")
        result = await self._nlp.polish(summary.summary_text, language=language)
        await self._polishes.create(
            document_summary_id=summary_id,
            model=result["model"],
            polished_text=result["polished_markdown"],
        )
        await self._session.commit()
        return result["polished_markdown"], result["model"]
