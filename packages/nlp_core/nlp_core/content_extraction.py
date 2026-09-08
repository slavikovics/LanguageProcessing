
from __future__ import annotations

from readability import Document
from readability.readability import Unparseable

from .tokenization import clean_html


def extract_main_content(html: str) -> str:
    try:
        main_html = Document(html).summary(html_partial=True)
    except Unparseable:
        return clean_html(html)
    text = clean_html(main_html)
    return text if text else clean_html(html)
