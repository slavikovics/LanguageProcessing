
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class NlpServiceClient:
    EMBEDDING_TIMEOUT = 300.0

    def __init__(self, base_url: str | None = None, *, timeout: float = 60.0) -> None:
        self._base_url = base_url or get_settings().nlp_service_url
        self._timeout = timeout

    async def _post(
        self, path: str, payload: dict[str, Any], *, timeout: float | None = None
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=timeout or self._timeout) as client:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            return response.json()

    async def lemmatize(self, text: str) -> list[str]:
        body = await self._post("/lemmatize", {"text": text})
        return body["lemmas"]

    async def lemmatize_batch(self, texts: list[str]) -> list[list[str]]:
        body = await self._post("/lemmatize-batch", {"texts": texts})
        return body["lemmas"]

    async def index(self, document_term_lists: list[list[str]]) -> dict[str, Any]:
        return await self._post("/index", {"document_term_lists": document_term_lists})

    async def idf_from_frequency(
        self, document_frequency: dict[str, int], total_documents: int
    ) -> dict[str, float]:
        body = await self._post(
            "/idf-from-frequency",
            {"document_frequency": document_frequency, "total_documents": total_documents},
        )
        return body["idf"]

    async def document_vector(
        self, term_frequencies: dict[str, int], idf: dict[str, float]
    ) -> dict[str, float]:
        body = await self._post(
            "/document-vector", {"term_frequencies": term_frequencies, "idf": idf}
        )
        return body["vector"]

    async def evaluate_metrics(self, ranked_ids: list[int], relevant_ids: list[int]) -> dict[str, Any]:
        return await self._post(
            "/metrics/evaluate", {"ranked_ids": ranked_ids, "relevant_ids": relevant_ids}
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        body = await self._post(
            "/embeddings/documents", {"texts": texts}, timeout=self.EMBEDDING_TIMEOUT
        )
        return body["vectors"]

    async def embed_query(self, text: str) -> list[float]:
        body = await self._post(
            "/embeddings/query", {"text": text}, timeout=self.EMBEDDING_TIMEOUT
        )
        return body["vector"]
