
from __future__ import annotations

import os

import httpx

MT_SERVICE_URL = os.environ.get("MT_SERVICE_URL", "http://mt-service:8005")


async def translate_sentences(sentences: list[str]) -> list[str]:
    if not sentences:
        return []
    async with httpx.AsyncClient(base_url=MT_SERVICE_URL, timeout=280.0) as client:
        response = await client.post("/translate", json={"sentences": sentences})
        response.raise_for_status()
        return response.json()["translations"]
