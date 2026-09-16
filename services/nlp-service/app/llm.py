
from __future__ import annotations

import asyncio
import os

import httpx

MODEL_NAME = os.environ.get("OPENROUTER_CHAT_MODEL", "qwen/qwen3.8-flash")

_API_URL = "https://openrouter.ai/api/v1/chat/completions"

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 2.0

_SYSTEM_PROMPT = (
    "You are a copy-editing assistant for an extractive text-summarization tool. "
    "You are given sentences that an algorithm already selected as the most important "
    "ones from a source document. Your ONLY task is to lightly polish them into a "
    "clean, coherent passage: fix grammar, smooth the transitions between sentences, "
    "and resolve obviously dangling pronouns/references when the antecedent is already "
    "present in the given text.\n\n"
    "Strict rules:\n"
    "1. Do NOT add any fact, number, claim, or detail that is not already present in "
    "the input sentences.\n"
    "2. Do NOT omit or change the meaning of any of the given sentences.\n"
    "3. Do NOT summarize further — keep all the given information.\n"
    "4. Write in the same language as the input text.\n"
    "5. Respond in Markdown: plain paragraphs are enough, only use headings, lists or "
    "emphasis if they genuinely improve readability of this exact content."
)


class LlmConfigError(RuntimeError):
    pass


def _api_key() -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise LlmConfigError("OPENROUTER_API_KEY is not set — required for LLM polishing")
    return api_key


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


async def polish(text: str, *, language: str | None = None) -> str:
    api_key = _api_key()
    user_content = text if not language else f"[language: {language}]\n\n{text}"
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
    }

    for attempt in range(_MAX_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    _API_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if attempt == _MAX_ATTEMPTS - 1 or not _is_retryable(exc):
                raise
            await asyncio.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
