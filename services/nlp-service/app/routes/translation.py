import asyncio
import dataclasses

from fastapi import APIRouter
from nlp_core import tokenization, transfer_translation, translation

from app import mt_client
from app.schemas.translation import (
    DiffSegmentOut,
    TranslatedWordOut,
    TranslateRequest,
    TranslateResponse,
    WordListRequest,
    WordListResponse,
)

router = APIRouter(tags=["translation"])

_TRANSLATORS = {
    "direct": translation.translate,
    "transfer": transfer_translation.transfer_translate,
}


async def _translate_neural(text: str, dictionary: dict[str, str]) -> translation.TranslationResult:
    stats = await asyncio.to_thread(translation.translate, text, dictionary)
    sentences = await asyncio.to_thread(tokenization.split_sentences, text)
    translated_sentences = await mt_client.translate_sentences(sentences)
    return dataclasses.replace(stats, translated_text=" ".join(translated_sentences))


@router.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest) -> TranslateResponse:
    if payload.method == "neural":
        result = await _translate_neural(payload.text, payload.dictionary)
    else:
        result = await asyncio.to_thread(
            _TRANSLATORS[payload.method], payload.text, payload.dictionary
        )
    return TranslateResponse(
        translated_text=result.translated_text,
        word_count=result.word_count,
        translated_word_count=result.translated_word_count,
        words=[TranslatedWordOut.model_validate(word) for word in result.words],
        diff_segments=[DiffSegmentOut.model_validate(seg) for seg in result.diff_segments],
    )


@router.post("/translate/word-list", response_model=WordListResponse)
async def word_list(payload: WordListRequest) -> WordListResponse:
    words = await asyncio.to_thread(
        translation.build_word_list, payload.text, payload.dictionary
    )
    return WordListResponse(words=[TranslatedWordOut.model_validate(word) for word in words])
