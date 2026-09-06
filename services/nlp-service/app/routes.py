import asyncio

from fastapi import APIRouter
from nlp_core import metrics, similarity, tokenization, weighting

from app import embeddings
from app.schemas import (
    DocumentVectorRequest,
    EmbedDocumentsRequest,
    EmbedDocumentsResponse,
    EmbedQueryRequest,
    EmbedQueryResponse,
    IdfFromFrequencyRequest,
    IdfFromFrequencyResponse,
    IdfRequest,
    IdfResponse,
    IndexRequest,
    IndexResponse,
    LemmatizeBatchRequest,
    LemmatizeBatchResponse,
    LemmatizeRequest,
    LemmatizeResponse,
    MetricsEvaluateRequest,
    MetricsEvaluateResponse,
    QueryVectorRequest,
    SimilarityRequest,
    SimilarityResponse,
    TokenizeRequest,
    TokenizeResponse,
    VectorResponse,
)

router = APIRouter(tags=["nlp"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/tokenize", response_model=TokenizeResponse)
async def tokenize(payload: TokenizeRequest) -> TokenizeResponse:
    tokens = tokenization.tokenize(payload.text, keep_stopwords=payload.keep_stopwords)
    return TokenizeResponse(tokens=tokens)


@router.post("/lemmatize", response_model=LemmatizeResponse)
async def lemmatize(payload: LemmatizeRequest) -> LemmatizeResponse:
    return LemmatizeResponse(lemmas=tokenization.lemmatize(payload.text))


@router.post("/lemmatize-batch", response_model=LemmatizeBatchResponse)
async def lemmatize_batch(payload: LemmatizeBatchRequest) -> LemmatizeBatchResponse:
    """Uses spaCy's nlp.pipe() (via lemmatize_many) instead of one nlp() call
    per text — meaningfully faster for the document-batch case an indexing
    job sends (see IndexingService). Run in a worker thread like
    /embeddings/documents: CPU-bound spaCy processing would otherwise block
    this single-process event loop for the whole batch.
    """
    lemmas = await asyncio.to_thread(tokenization.lemmatize_many, payload.texts)
    return LemmatizeBatchResponse(lemmas=lemmas)


@router.post("/idf", response_model=IdfResponse)
async def compute_idf(payload: IdfRequest) -> IdfResponse:
    total_documents = len(payload.document_term_lists)
    document_frequency = weighting.document_frequencies(payload.document_term_lists)
    idf = weighting.inverse_document_frequency(document_frequency, total_documents)
    return IdfResponse(total_documents=total_documents, document_frequency=document_frequency, idf=idf)


@router.post("/document-vector", response_model=VectorResponse)
async def document_vector(payload: DocumentVectorRequest) -> VectorResponse:
    vector = weighting.normalized_tfidf_vector(payload.term_frequencies, payload.idf)
    return VectorResponse(vector=vector)


@router.post("/query-vector", response_model=VectorResponse)
async def query_vector(payload: QueryVectorRequest) -> VectorResponse:
    return VectorResponse(vector=weighting.binary_query_vector(payload.terms))


@router.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity(payload: SimilarityRequest) -> SimilarityResponse:
    return SimilarityResponse(score=similarity.cosine_similarity(payload.a, payload.b))


@router.post("/index", response_model=IndexResponse)
async def index_documents(payload: IndexRequest) -> IndexResponse:
    """Full-corpus indexing step: given one lemma list per document, computes
    the collection's IDF (1.5) plus each document's raw term frequencies and
    normalized TF-IDF vector (1.6 + L2 norm) in one round trip — the
    `/index` endpoint referenced by docs/ARCHITECTURE.md.
    """
    total_documents = len(payload.document_term_lists)
    document_frequency = weighting.document_frequencies(payload.document_term_lists)
    idf = weighting.inverse_document_frequency(document_frequency, total_documents)
    term_frequencies = [weighting.term_frequencies(terms) for terms in payload.document_term_lists]
    vectors = [
        weighting.normalized_tfidf_vector(freqs, idf) for freqs in term_frequencies
    ]
    return IndexResponse(idf=idf, term_frequencies=term_frequencies, vectors=vectors)


@router.post("/idf-from-frequency", response_model=IdfFromFrequencyResponse)
async def idf_from_frequency(payload: IdfFromFrequencyRequest) -> IdfFromFrequencyResponse:
    """Recomputes IDF (1.5) straight from already-known document frequencies —
    used at search time, when the caller derives document_frequency from the
    `document_terms` table instead of resending every document's term list.
    """
    idf = weighting.inverse_document_frequency(payload.document_frequency, payload.total_documents)
    return IdfFromFrequencyResponse(idf=idf)


@router.post("/embeddings/documents", response_model=EmbedDocumentsResponse)
async def embed_documents(payload: EmbedDocumentsRequest) -> EmbedDocumentsResponse:
    """Batch-encode document texts with the dense embedding model (see
    app/embeddings.py) — the second search model's counterpart to /index.

    encode_documents() is synchronous, CPU-bound torch inference that can
    run for minutes on a real document batch; run it in a worker thread via
    asyncio.to_thread so it doesn't block this single-process event loop —
    without this, every other concurrent request (including unrelated
    /lemmatize calls for a different collection) would stall until the
    encode finishes.
    """
    vectors = await asyncio.to_thread(embeddings.encode_documents, payload.texts)
    return EmbedDocumentsResponse(vectors=vectors)


@router.post("/embeddings/query", response_model=EmbedQueryResponse)
async def embed_query(payload: EmbedQueryRequest) -> EmbedQueryResponse:
    vector = await asyncio.to_thread(embeddings.encode_query, payload.text)
    return EmbedQueryResponse(vector=vector)


@router.post("/metrics/evaluate", response_model=MetricsEvaluateResponse)
async def evaluate_metrics(payload: MetricsEvaluateRequest) -> MetricsEvaluateResponse:
    """The full ROMIP'2004 search-track metric set for one ranked list
    against its qrels (see tasks/romip_metrics.pdf): Precision/Recall/F1
    over the whole list, Precision(5), Precision(10), Average Precision,
    R-Precision, and the 11-point interpolated curve.
    """
    relevant = set(payload.relevant_ids)
    n = len(payload.ranked_ids)
    precision = metrics.precision_at_k(payload.ranked_ids, relevant, n)
    recall = metrics.recall_at_k(payload.ranked_ids, relevant, n)
    return MetricsEvaluateResponse(
        retrieved_count=n,
        relevant_count=len(relevant),
        precision=precision,
        recall=recall,
        f1=metrics.f1_score(precision, recall),
        precision_at_5=metrics.precision_at_k(payload.ranked_ids, relevant, 5),
        precision_at_10=metrics.precision_at_k(payload.ranked_ids, relevant, 10),
        average_precision=metrics.average_precision(payload.ranked_ids, relevant),
        r_precision=metrics.r_precision(payload.ranked_ids, relevant),
        curve=metrics.interpolated_precision_recall(payload.ranked_ids, relevant),
    )
