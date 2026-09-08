
from __future__ import annotations

import urllib.robotparser as robotparser
from urllib.parse import urlsplit, urlunsplit

import httpx


class RobotsCache:
    def __init__(self, user_agent: str, client: httpx.AsyncClient) -> None:
        self._user_agent = user_agent
        self._client = client
        self._parsers: dict[str, robotparser.RobotFileParser] = {}

    async def is_allowed(self, url: str) -> bool:
        origin = _origin(url)
        parser = self._parsers.get(origin)
        if parser is None:
            parser = await self._load(origin)
            self._parsers[origin] = parser
        return parser.can_fetch(self._user_agent, url)

    async def _load(self, origin: str) -> robotparser.RobotFileParser:
        parser = robotparser.RobotFileParser()
        robots_url = f"{origin}/robots.txt"
        try:
            response = await self._client.get(robots_url, timeout=5.0)
            if response.status_code >= 400:
                parser.parse([])
            else:
                parser.parse(response.text.splitlines())
        except httpx.HTTPError:
            parser.parse([])
        return parser


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))
