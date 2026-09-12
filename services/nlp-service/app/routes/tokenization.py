import asyncio

from fastapi import APIRouter
from nlp_core import tokenization

from app.schemas.tokenization import (
    LemmatizeBatchRequest,
    LemmatizeBatchResponse,
    LemmatizeRequest,
    LemmatizeResponse,
    SplitSentencesRequest,
    SplitSentencesResponse,
    TokenizeRequest,
    TokenizeResponse,
)

router = APIRouter(tags=["nlp"])


@router.post("/tokenize", response_model=TokenizeResponse)
async def tokenize(payload: TokenizeRequest) -> TokenizeResponse:
    tokens = tokenization.tokenize(payload.text, keep_stopwords=payload.keep_stopwords)
    return TokenizeResponse(tokens=tokens)


@router.post("/lemmatize", response_model=LemmatizeResponse)
async def lemmatize(payload: LemmatizeRequest) -> LemmatizeResponse:
    return LemmatizeResponse(lemmas=tokenization.lemmatize(payload.text))


@router.post("/lemmatize-batch", response_model=LemmatizeBatchResponse)
async def lemmatize_batch(payload: LemmatizeBatchRequest) -> LemmatizeBatchResponse:
    lemmas = await asyncio.to_thread(tokenization.lemmatize_many, payload.texts)
    return LemmatizeBatchResponse(lemmas=lemmas)


@router.post("/sentences", response_model=SplitSentencesResponse)
async def split_sentences(payload: SplitSentencesRequest) -> SplitSentencesResponse:
    sentences = await asyncio.to_thread(tokenization.split_sentences, payload.text)
    return SplitSentencesResponse(sentences=sentences)
