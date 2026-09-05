"""Thin async HTTP client for nlp-service — the only place `api` knows that
service exists. Keeps every NLP formula (tokenization, TF/IDF, cosine) in
`nlp_core`/`nlp-service`; `api` only ever sees JSON in and out.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class NlpServiceClient:
    # Batch-encoding documents with a CPU transformer model (see
    # nlp-service's app/embeddings.py) is meaningfully slower than every
    # other call this client makes — it runs inside a background IndexJob,
    # not an interactive request, so a much longer timeout is fine here.
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
        """Returns {idf, term_frequencies, vectors} — see nlp-service's /index."""
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
        """The full ROMIP'2004 search-track metric set for one ranked list
        against its qrels: whole-list Precision/Recall/F1, Precision(5),
        Precision(10), Average Precision, R-Precision, 11-point curve."""
        return await self._post(
            "/metrics/evaluate", {"ranked_ids": ranked_ids, "relevant_ids": relevant_ids}
        )

    async def aggregate_metrics(self, runs: list[tuple[list[int], list[int]]]) -> dict[str, Any]:
        """MAP (macro-average of AP) plus micro-averaged precision/recall/F1
        over several query runs — see nlp-service's /metrics/aggregate."""
        return await self._post(
            "/metrics/aggregate",
            {"runs": [{"ranked_ids": ranked, "relevant_ids": relevant} for ranked, relevant in runs]},
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
