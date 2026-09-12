import time

from fastapi import APIRouter
from nlp_core import summarization

from app.schemas import (
    AlgorithmicSummarizeRequest,
    EmbeddingSummarizeRequest,
    KeywordGroup,
    KeywordHierarchyRequest,
    KeywordHierarchyResponse,
    SelectedSentence,
    SummarizeResponse,
    TextRankSummarizeRequest,
)

router = APIRouter(tags=["summarization"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _to_response(
    scores: list[summarization.SentenceScore], sentence_count: int, elapsed_ms: float
) -> SummarizeResponse:
    selected = summarization.select_summary_sentences(scores, sentence_count)
    return SummarizeResponse(
        selected=[
            SelectedSentence(index=s.index, text=s.text, weight=s.weight) for s in selected
        ],
        total_sentences=len(scores),
        elapsed_ms=elapsed_ms,
    )


@router.post("/summarize/algorithmic", response_model=SummarizeResponse)
async def summarize_algorithmic(payload: AlgorithmicSummarizeRequest) -> SummarizeResponse:
    started = time.perf_counter()
    scores = summarization.rank_sentences_algorithm(payload.text, payload.term_weights)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return _to_response(scores, payload.sentence_count, elapsed_ms)


@router.post("/summarize/textrank", response_model=SummarizeResponse)
async def summarize_textrank(payload: TextRankSummarizeRequest) -> SummarizeResponse:
    started = time.perf_counter()
    scores = summarization.rank_sentences_textrank(payload.text)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return _to_response(scores, payload.sentence_count, elapsed_ms)


@router.post("/summarize/embeddings", response_model=SummarizeResponse)
async def summarize_embeddings(payload: EmbeddingSummarizeRequest) -> SummarizeResponse:
    started = time.perf_counter()
    scores = summarization.rank_sentences_by_embedding_centrality(
        payload.sentences, payload.embeddings
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return _to_response(scores, payload.sentence_count, elapsed_ms)


@router.post("/keywords/hierarchy", response_model=KeywordHierarchyResponse)
async def keywords_hierarchy(payload: KeywordHierarchyRequest) -> KeywordHierarchyResponse:
    groups = summarization.extract_keyword_hierarchy(
        payload.term_weights,
        payload.text,
        top_n=payload.top_n,
        max_children=payload.max_children,
    )
    return KeywordHierarchyResponse(
        groups=[KeywordGroup(term=g.term, children=g.children) for g in groups]
    )
