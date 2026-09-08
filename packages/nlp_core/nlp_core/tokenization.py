
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

_UNICODE_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)


@dataclass(frozen=True)
class Token:
    text: str
    lemma: str
    pos: str
    is_stop: bool


def _load_spacy_pipeline():
    import spacy

    try:
        nlp = spacy.load("en_core_web_sm", exclude=["parser", "ner"])
    except OSError as exc:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is not installed. "
            "Run: python -m spacy download en_core_web_sm"
        ) from exc
    nlp.add_pipe("sentencizer")
    nlp.max_length = 5_000_000
    return nlp


@lru_cache(maxsize=1)
def get_pipeline():
    return _load_spacy_pipeline()


def clean_html(html: str) -> str:
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
    return [t.lemma for t in tokenize(text)]


def lemmatize_many(texts: list[str], *, batch_size: int = 50) -> list[list[str]]:
    if not texts:
        return []
    pipeline = get_pipeline()
    return [
        [tok.lemma_.lower() for tok in doc if tok.is_alpha and not tok.is_stop]
        for doc in pipeline.pipe(texts, batch_size=batch_size)
    ]


def simple_word_tokenize(text: str) -> list[str]:
    return [w.lower() for w in _UNICODE_WORD_RE.findall(text)]


def char_ngrams(text: str, n: int = 5) -> list[str]:
    words = _WORD_RE.findall(text.lower())
    grams: list[str] = []
    for word in words:
        padded = f" {word} "
        for i in range(len(padded) - n + 1):
            grams.append(padded[i : i + n])
    return grams
