"""Dense-embedding encoding for the second search model, via OpenRouter's
hosted embeddings API (https://openrouter.ai/docs/api_reference/embeddings)
instead of a locally-run sentence-transformers model.

Uses Qwen3-Embedding-8B — ranked #1 on the MTEB multilingual leaderboard
(100+ languages) as of the model's release, with a 32K-token context, at
roughly $0.01 per million input tokens (OpenRouter, comparable providers).
Its native output is a 4096-dim vector — see ips_db.models.MAX_EMBEDDING_DIM,
sized to hold it.

Unlike the E5 family this service previously ran locally, documents need no
instruction prefix. Queries do: Qwen3-Embedding's own usage guidance reports
instruction-aware query prompting improves retrieval by roughly 1-5% over an
unprefixed query, so encode_query() applies one fixed retrieval instruction
(see _QUERY_INSTRUCTION) to every query.
"""

from __future__ import annotations

import asyncio
import os

import httpx

MODEL_NAME = os.environ.get("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
NATIVE_DIM = 4096

_API_URL = "https://openrouter.ai/api/v1/embeddings"

_QUERY_INSTRUCTION = (
    "Instruct: Given a web search query, retrieve relevant passages that answer the query\n"
    "Query: {query}"
)

# Keeps any single request body (and the provider-side batch it triggers)
# well clear of OpenRouter/provider request-size limits — course-project
# collections run to at most a few hundred chunks per indexing pass.
_BATCH_SIZE = 64

# encode_documents() fires up to this many batch requests to OpenRouter
# concurrently instead of one at a time — indexing time here is almost
# entirely network round-trip latency (the model itself runs on OpenRouter's
# infrastructure, not this process), so overlapping requests turns wall-clock
# time into roughly (batches / this) round trips instead of one per batch.
_MAX_CONCURRENT_REQUESTS = int(os.environ.get("OPENROUTER_EMBEDDING_CONCURRENCY", "10"))


class EmbeddingConfigError(RuntimeError):
    """Raised when OPENROUTER_API_KEY isn't set. Dense-embedding search is
    optional — TF-IDF search keeps working without it — so this is only
    raised when a caller actually requests an embedding."""


def _api_key() -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise EmbeddingConfigError(
            "OPENROUTER_API_KEY is not set — required for dense-embedding search"
        )
    return api_key


async def _embed_batch(client: httpx.AsyncClient, api_key: str, texts: list[str]) -> list[list[float]]:
    response = await client.post(
        _API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": MODEL_NAME, "input": texts, "encoding_format": "float"},
    )
    response.raise_for_status()
    data = response.json()["data"]
    return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]


async def encode_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    api_key = _api_key()
    batches = [texts[start : start + _BATCH_SIZE] for start in range(0, len(texts), _BATCH_SIZE)]
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)

    async def _bounded(client: httpx.AsyncClient, batch: list[str]) -> list[list[float]]:
        async with semaphore:
            return await _embed_batch(client, api_key, batch)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # gather preserves the batches' order in its results, so vectors stay
        # aligned with the input texts despite completing out of order.
        batch_results = await asyncio.gather(*(_bounded(client, batch) for batch in batches))
    return [vector for batch_vectors in batch_results for vector in batch_vectors]


async def encode_query(text: str) -> list[float]:
    api_key = _api_key()
    async with httpx.AsyncClient(timeout=120.0) as client:
        vectors = await _embed_batch(client, api_key, [_QUERY_INSTRUCTION.format(query=text)])
    return vectors[0]
