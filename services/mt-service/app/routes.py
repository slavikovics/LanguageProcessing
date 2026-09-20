from __future__ import annotations

import asyncio

from fastapi import APIRouter

from app import model
from app.schemas import TranslateRequest, TranslateResponse

router = APIRouter(tags=["mt"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/translate", response_model=TranslateResponse)
async def translate(payload: TranslateRequest) -> TranslateResponse:
    translations = await asyncio.to_thread(model.translate_batch, payload.sentences)
    return TranslateResponse(translations=translations)
