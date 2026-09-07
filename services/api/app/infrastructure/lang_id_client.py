"""Thin async HTTP client for lang-id-service — the only place `api` knows
that service exists. Keeps every language-ID formula (frequent-words,
alphabetic, the PyTorch neural classifier) in lang-id-service; `api` only
ever sees JSON in and out, exactly like NlpServiceClient/nlp-service.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class LangIdServiceClient:
    def __init__(self, base_url: str | None = None, *, timeout: float = 60.0) -> None:
        self._base_url = base_url or get_settings().lang_id_service_url
        self._timeout = timeout

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            return response.json()

    async def build_frequent_words_profile(self, texts: list[str], *, top_n: int = 300) -> list[str]:
        body = await self._post("/frequent-words/profile", {"texts": texts, "top_n": top_n})
        return body["top_words"]

    async def identify_frequent_words(
        self, top_words_by_language: dict[str, list[str]], text: str
    ) -> dict[str, Any]:
        return await self._post(
            "/frequent-words/identify",
            {"top_words_by_language": top_words_by_language, "text": text},
        )

    async def build_alphabetic_profile(self, texts: list[str]) -> dict[str, float]:
        body = await self._post("/alphabetic/profile", {"texts": texts})
        return body["frequencies"]

    async def identify_alphabetic(
        self, profiles_by_language: dict[str, dict[str, float]], text: str
    ) -> dict[str, Any]:
        return await self._post(
            "/alphabetic/identify",
            {"profiles_by_language": profiles_by_language, "text": text},
        )

    async def train_neural_step(
        self,
        vectors_by_language: dict[str, list[list[float]]],
        *,
        weights: list[list[float]] | None = None,
        bias: list[float] | None = None,
        classes: list[str] | None = None,
        epochs: int = 10,
        learning_rate: float = 0.01,
        weight_decay: float = 1e-3,
    ) -> dict[str, Any]:
        return await self._post(
            "/neural/train-step",
            {
                "vectors_by_language": vectors_by_language,
                "weights": weights,
                "bias": bias,
                "classes": classes,
                "epochs": epochs,
                "learning_rate": learning_rate,
                "weight_decay": weight_decay,
            },
        )

    async def identify_neural(
        self, weights: list[list[float]], bias: list[float], classes: list[str], vector: list[float]
    ) -> dict[str, Any]:
        return await self._post(
            "/neural/identify",
            {"weights": weights, "bias": bias, "classes": classes, "vector": vector},
        )
