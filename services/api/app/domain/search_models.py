
from __future__ import annotations

from typing import Protocol

from ips_db import Collection, SearchModel


class SearchBackend(Protocol):
    async def rank(
        self, *, collection: Collection, text: str, model_row: SearchModel
    ) -> list[tuple[int, float]]:
        ...
