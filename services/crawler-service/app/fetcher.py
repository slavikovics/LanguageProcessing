"""HTTP fetch + link/title extraction. Text cleanup itself lives in
nlp_core.tokenization.clean_html so the crawler and any future lab share the
same normalization."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup


class FetchError(Exception):
    pass


async def fetch_html(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url, timeout=10.0, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        raise FetchError(f"unsupported content-type: {content_type!r}")
    return response.text


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        lowered = href.lower()
        if not href or lowered.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        parts = urlsplit(absolute)
        if parts.scheme not in {"http", "https"}:
            continue
        links.append(urlsplit(absolute)._replace(fragment="").geturl())
    return links


def extract_title(html: str, *, fallback: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string and soup.title.string.strip():
        return soup.title.string.strip()[:500]
    return fallback[:500]
