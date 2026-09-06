"""HTML cleanup, sentence splitting, tokenization/lemmatization (English, via
spaCy) and character n-grams. Side-effect free (no DB, no network) so it's
easy to unit test and reuse across callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


@dataclass(frozen=True)
class Token:
    text: str
    lemma: str
    pos: str
    is_stop: bool


def _load_spacy_pipeline():
    import spacy

    try:
        return spacy.load("en_core_web_sm")
    except OSError as exc:  # pragma: no cover - exercised only without the model
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is not installed. "
            "Run: python -m spacy download en_core_web_sm"
        ) from exc


@lru_cache(maxsize=1)
def get_pipeline():
    """Lazily load and cache the spaCy pipeline (expensive to construct)."""
    return _load_spacy_pipeline()


def clean_html(html: str) -> str:
    """Strip tags/scripts/styles from a raw HTML page and collapse whitespace."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    doc = get_pipeline()(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def tokenize(text: str, *, keep_stopwords: bool = False) -> list[Token]:
    """Alphabetic tokens only — numbers and punctuation are dropped."""
    doc = get_pipeline()(text)
    tokens: list[Token] = []
    for tok in doc:
        if not tok.is_alpha:
            continue
        if not keep_stopwords and tok.is_stop:
            continue
        tokens.append(
            Token(
                text=tok.text.lower(),
                lemma=tok.lemma_.lower(),
                pos=tok.pos_,
                is_stop=tok.is_stop,
            )
        )
    return tokens


def lemmatize(text: str) -> list[str]:
    """Convenience: just the lemma strings used as index terms."""
    return [t.lemma for t in tokenize(text)]


def lemmatize_many(texts: list[str], *, batch_size: int = 50) -> list[list[str]]:
    """Batch lemmatize via spaCy's nlp.pipe(), far faster than one nlp() call per text."""
    if not texts:
        return []
    pipeline = get_pipeline()
    return [
        [tok.lemma_.lower() for tok in doc if tok.is_alpha and not tok.is_stop]
        for doc in pipeline.pipe(texts, batch_size=batch_size)
    ]


def char_ngrams(text: str, n: int = 5) -> list[str]:
    """Word-boundary-padded character n-grams, e.g. char_ngrams("the", 5) -> [" the "]."""
    words = _WORD_RE.findall(text.lower())
    grams: list[str] = []
    for word in words:
        padded = f" {word} "
        for i in range(len(padded) - n + 1):
            grams.append(padded[i : i + n])
    return grams
