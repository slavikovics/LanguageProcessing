from fastapi import APIRouter

from app import alphabetic, frequent_words, neural
from app.schemas import (
    AlphabeticIdentifyRequest,
    AlphabeticProfileRequest,
    AlphabeticProfileResponse,
    FrequentWordsIdentifyRequest,
    FrequentWordsProfileRequest,
    FrequentWordsProfileResponse,
    IdentifyResponse,
    NeuralIdentifyRequest,
    NeuralIdentifyResponse,
    NeuralTrainStepRequest,
    NeuralTrainStepResponse,
)

router = APIRouter(tags=["lang-id"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/frequent-words/profile", response_model=FrequentWordsProfileResponse)
async def frequent_words_profile(payload: FrequentWordsProfileRequest) -> FrequentWordsProfileResponse:
    return FrequentWordsProfileResponse(
        top_words=frequent_words.build_profile(payload.texts, top_n=payload.top_n)
    )


@router.post("/frequent-words/identify", response_model=IdentifyResponse)
async def frequent_words_identify(payload: FrequentWordsIdentifyRequest) -> IdentifyResponse:
    return IdentifyResponse(**frequent_words.identify(payload.top_words_by_language, payload.text))


@router.post("/alphabetic/profile", response_model=AlphabeticProfileResponse)
async def alphabetic_profile(payload: AlphabeticProfileRequest) -> AlphabeticProfileResponse:
    return AlphabeticProfileResponse(frequencies=alphabetic.build_profile(payload.texts))


@router.post("/alphabetic/identify", response_model=IdentifyResponse)
async def alphabetic_identify(payload: AlphabeticIdentifyRequest) -> IdentifyResponse:
    return IdentifyResponse(**alphabetic.identify(payload.profiles_by_language, payload.text))


@router.post("/neural/train-step", response_model=NeuralTrainStepResponse)
async def neural_train_step(payload: NeuralTrainStepRequest) -> NeuralTrainStepResponse:
    """Runs a small, resumable chunk of gradient-descent epochs — see
    app.neural.train_step for why training is chunked instead of one long
    call: it's what lets api's background task report live progress."""
    result = neural.train_step(
        payload.vectors_by_language,
        weights=payload.weights,
        bias=payload.bias,
        classes=payload.classes,
        epochs=payload.epochs,
        learning_rate=payload.learning_rate,
        weight_decay=payload.weight_decay,
    )
    return NeuralTrainStepResponse(**result)


@router.post("/neural/identify", response_model=NeuralIdentifyResponse)
async def neural_identify(payload: NeuralIdentifyRequest) -> NeuralIdentifyResponse:
    return NeuralIdentifyResponse(
        **neural.identify(payload.weights, payload.bias, payload.classes, payload.vector)
    )
