
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class SummarizationServiceClient:
    def __init__(self, base_url: str | None = None, *, timeout: float = 120.0) -> None:
        self._base_url = base_url or get_settings().summarization_service_url
        self._timeout = timeout

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            return response.json()

    async def summarize_algorithmic(
        self, text: str, term_weights: dict[str, float], sentence_count: int
    ) -> dict[str, Any]:
        return await self._post(
            "/summarize/algorithmic",
            {"text": text, "term_weights": term_weights, "sentence_count": sentence_count},
        )

    async def summarize_textrank(self, text: str, sentence_count: int) -> dict[str, Any]:
        return await self._post(
            "/summarize/textrank", {"text": text, "sentence_count": sentence_count}
        )

    async def summarize_embeddings(
        self,
        sentences: list[str],
        embeddings: list[list[float]],
        sentence_count: int,
        *,
        query_embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "/summarize/embeddings",
            {
                "sentences": sentences,
                "embeddings": embeddings,
                "sentence_count": sentence_count,
                "query_embedding": query_embedding,
            },
        )

    async def extract_keyword_hierarchy(
        self,
        text: str,
        term_weights: dict[str, float],
        *,
        top_n: int | None = None,
        max_children: int = 5,
    ) -> list[dict[str, Any]]:
        body = await self._post(
            "/keywords/hierarchy",
            {"text": text, "term_weights": term_weights, "top_n": top_n, "max_children": max_children},
        )
        return body["groups"]
