"""Strips page chrome — navigation, headers, footers, sidebars, ad slots —
before the raw-tag cleanup in nlp_core.tokenization.clean_html runs, so the
indexed text is the article/body content a page is actually about, not the
site furniture repeated on every page. Uses readability-lxml, the Python
port of Mozilla's Readability algorithm (the same one behind Firefox's
Reader View), rather than hand-rolled heuristics.
"""

from __future__ import annotations

from readability import Document
from readability.readability import Unparseable
from nlp_core.tokenization import clean_html


def extract_main_content(html: str) -> str:
    try:
        main_html = Document(html).summary(html_partial=True)
    except Unparseable:
        return clean_html(html)
    text = clean_html(main_html)
    # Readability sometimes isolates a near-empty fragment on pages with no
    # clear article body (landing pages, link hubs) — cleaning the whole
    # page beats indexing nothing for those.
    return text if text else clean_html(html)
