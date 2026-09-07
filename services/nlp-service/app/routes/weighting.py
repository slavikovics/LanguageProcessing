from fastapi import APIRouter
from nlp_core import similarity, weighting

from app.schemas.weighting import (
    DocumentVectorRequest,
    IdfFromFrequencyRequest,
    IdfFromFrequencyResponse,
    IdfRequest,
    IdfResponse,
    IndexRequest,
    IndexResponse,
    QueryVectorRequest,
    SimilarityRequest,
    SimilarityResponse,
    VectorResponse,
)

router = APIRouter(tags=["nlp"])


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
    vectors = [weighting.normalized_tfidf_vector(freqs, idf) for freqs in term_frequencies]
    return IndexResponse(idf=idf, term_frequencies=term_frequencies, vectors=vectors)


@router.post("/idf-from-frequency", response_model=IdfFromFrequencyResponse)
async def idf_from_frequency(payload: IdfFromFrequencyRequest) -> IdfFromFrequencyResponse:
    """Recomputes IDF from already-known document frequencies, used at search
    time instead of resending every document's term list."""
    idf = weighting.inverse_document_frequency(payload.document_frequency, payload.total_documents)
    return IdfFromFrequencyResponse(idf=idf)
