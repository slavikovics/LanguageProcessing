import asyncio

from fastapi import APIRouter
from nlp_core import translation

from app.schemas.translation import (
    TranslatedWordOut,
    TranslateRequest,
    TranslateResponse,
    WordListRequest,
    WordListResponse,
)

router = APIRouter(tags=["translation"])


@router.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest) -> TranslateResponse:
    result = await asyncio.to_thread(
        translation.translate, payload.text, payload.dictionary
    )
    return TranslateResponse(
        translated_text=result.translated_text,
        word_count=result.word_count,
        translated_word_count=result.translated_word_count,
        words=[TranslatedWordOut.model_validate(word) for word in result.words],
    )


@router.post("/translate/word-list", response_model=WordListResponse)
async def word_list(payload: WordListRequest) -> WordListResponse:
    words = await asyncio.to_thread(
        translation.build_word_list, payload.text, payload.dictionary
    )
    return WordListResponse(words=[TranslatedWordOut.model_validate(word) for word in words])
