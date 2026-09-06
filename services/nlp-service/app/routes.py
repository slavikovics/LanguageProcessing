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
    """Runs in a worker thread — CPU-bound spaCy processing would otherwise
    block this single-process event loop for the whole batch."""
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
    """Full-corpus indexing: given one lemma list per document, computes the
    collection's IDF plus each document's term frequencies and TF-IDF vector."""
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
    """Recomputes IDF from already-known document frequencies, used at search
    time instead of resending every document's term list."""
    idf = weighting.inverse_document_frequency(payload.document_frequency, payload.total_documents)
    return IdfFromFrequencyResponse(idf=idf)


@router.post("/embeddings/documents", response_model=EmbedDocumentsResponse)
async def embed_documents(payload: EmbedDocumentsRequest) -> EmbedDocumentsResponse:
    """Batch-encode document texts with the dense embedding model — the
    second search model's counterpart to /index. Awaits OpenRouter's hosted
    API directly, so no worker thread is needed."""
    vectors = await embeddings.encode_documents(payload.texts)
    return EmbedDocumentsResponse(vectors=vectors)


@router.post("/embeddings/query", response_model=EmbedQueryResponse)
async def embed_query(payload: EmbedQueryRequest) -> EmbedQueryResponse:
    vector = await embeddings.encode_query(payload.text)
    return EmbedQueryResponse(vector=vector)


@router.post("/metrics/evaluate", response_model=MetricsEvaluateResponse)
async def evaluate_metrics(payload: MetricsEvaluateRequest) -> MetricsEvaluateResponse:
    """Computes rank-quality metrics for one ranked list against its qrels."""
    relevant = set(payload.relevant_ids)
    n = len(payload.ranked_ids)
    precision_at_5 = metrics.precision_at_k(payload.ranked_ids, relevant, 5)
    precision_at_10 = metrics.precision_at_k(payload.ranked_ids, relevant, 10)
    recall_at_5 = metrics.recall_at_k(payload.ranked_ids, relevant, 5)
    recall_at_10 = metrics.recall_at_k(payload.ranked_ids, relevant, 10)
    return MetricsEvaluateResponse(
        retrieved_count=n,
        relevant_count=len(relevant),
        precision_at_5=precision_at_5,
        precision_at_10=precision_at_10,
        recall_at_5=recall_at_5,
        recall_at_10=recall_at_10,
        f1_at_5=metrics.f1_score(precision_at_5, recall_at_5),
        f1_at_10=metrics.f1_score(precision_at_10, recall_at_10),
        average_precision=metrics.average_precision(payload.ranked_ids, relevant),
        r_precision=metrics.r_precision(payload.ranked_ids, relevant),
        curve=metrics.interpolated_precision_recall(payload.ranked_ids, relevant),
    )
