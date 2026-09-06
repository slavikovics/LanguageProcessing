"""Per-domain request rate limiting."""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit


class DomainThrottle:
    """Enforces a minimum delay between requests to the same domain, locked
    per domain so concurrent fetchers queue up instead of racing the same
    last-fetch timestamp and both firing at once."""

    def __init__(self, delay_seconds: float) -> None:
        self._delay = delay_seconds
        self._last_fetch: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, domain: str) -> asyncio.Lock:
        lock = self._locks.get(domain)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[domain] = lock
        return lock

    async def wait(self, url: str) -> None:
        domain = urlsplit(url).netloc
        async with self._lock_for(domain):
            now = time.monotonic()
            last = self._last_fetch.get(domain)
            if last is not None:
                elapsed = now - last
                if elapsed < self._delay:
                    await asyncio.sleep(self._delay - elapsed)
            self._last_fetch[domain] = time.monotonic()
