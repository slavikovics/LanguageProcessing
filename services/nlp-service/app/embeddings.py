"""Dense-embedding encoding for the second search model, via OpenRouter's
hosted embeddings API (Qwen3-Embedding-8B, 4096-dim). Queries get a fixed
retrieval instruction prefix (_QUERY_INSTRUCTION) since the model's own
guidance reports this measurably improves retrieval; documents don't need one.
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

# Keeps each request body clear of OpenRouter's request-size limits.
_BATCH_SIZE = 64

# Batches run concurrently since indexing time here is network-latency bound.
_MAX_CONCURRENT_REQUESTS = int(os.environ.get("OPENROUTER_EMBEDDING_CONCURRENCY", "10"))


class EmbeddingConfigError(RuntimeError):
    """OPENROUTER_API_KEY isn't set; only raised when embeddings are actually requested."""


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
        # gather() preserves batch order, keeping vectors aligned with input texts.
        batch_results = await asyncio.gather(*(_bounded(client, batch) for batch in batches))
    return [vector for batch_vectors in batch_results for vector in batch_vectors]


async def encode_query(text: str) -> list[float]:
    api_key = _api_key()
    async with httpx.AsyncClient(timeout=120.0) as client:
        vectors = await _embed_batch(client, api_key, [_QUERY_INSTRUCTION.format(query=text)])
    return vectors[0]
