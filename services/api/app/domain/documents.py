
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

MAX_TITLE_LENGTH = 500
MAX_URL_LENGTH = 2000


class DocumentError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentInput:
    title: str
    url: str | None
    clean_text: str


def build_document_input(*, title: str, url: str | None, clean_text: str) -> DocumentInput:
    title = title.strip()
    clean_text = clean_text.strip()

    if not title:
        raise DocumentError("title must not be empty")
    if len(title) > MAX_TITLE_LENGTH:
        raise DocumentError(f"title must be at most {MAX_TITLE_LENGTH} characters")

    normalized_url: str | None = None
    if url is not None and url.strip():
        normalized_url = url.strip()
        parsed = urlparse(normalized_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DocumentError(f"'{normalized_url}' is not a valid http(s) URL")
        if len(normalized_url) > MAX_URL_LENGTH:
            raise DocumentError(f"url must be at most {MAX_URL_LENGTH} characters")

    if not clean_text:
        raise DocumentError("document text must not be empty")

    return DocumentInput(title=title, url=normalized_url, clean_text=clean_text)
