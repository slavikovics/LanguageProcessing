from fastapi import APIRouter
from nlp_core import similarity, tokenization, weighting

from app.schemas import (
    DocumentVectorRequest,
    IdfRequest,
    IdfResponse,
    LemmatizeRequest,
    LemmatizeResponse,
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
