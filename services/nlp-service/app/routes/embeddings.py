from fastapi import APIRouter

from app import embeddings
from app.schemas.embeddings import (
    EmbedDocumentsRequest,
    EmbedDocumentsResponse,
    EmbedQueryRequest,
    EmbedQueryResponse,
)

router = APIRouter(tags=["nlp"])


@router.post("/embeddings/documents", response_model=EmbedDocumentsResponse)
async def embed_documents(payload: EmbedDocumentsRequest) -> EmbedDocumentsResponse:
    vectors = await embeddings.encode_documents(payload.texts)
    return EmbedDocumentsResponse(vectors=vectors)


@router.post("/embeddings/query", response_model=EmbedQueryResponse)
async def embed_query(payload: EmbedQueryRequest) -> EmbedQueryResponse:
    vector = await embeddings.encode_query(payload.text)
    return EmbedQueryResponse(vector=vector)
