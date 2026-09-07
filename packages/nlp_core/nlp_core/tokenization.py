"""HTML cleanup, sentence splitting, tokenization/lemmatization (English, via
spaCy) and character n-grams. Side-effect free (no DB, no network) so it's
easy to unit test and reuse across callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

# Unicode-letter based (not the ASCII-only _WORD_RE above), so accented
# letters survive — needed for LR2's French/English frequent-words and
# alphabetic methods, which must not depend on the English-only spaCy path
# below.
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
        # tokenize()/lemmatize() only ever read tok.is_alpha/is_stop (lexical,
        # need no pipeline component), tok.pos_ (tagger) and tok.lemma_
        # (attribute_ruler + lemmatizer) — never doc.ents or the dependency
        # tree, so "parser" and "ner" are dead weight here. They're also
        # exactly the two components spaCy's own docs blame for needing
        # roughly 1GB per 100,000 input characters, which is what forces the
        # conservative default nlp.max_length=1_000_000 (a real crawled page
        # can exceed that). Excluding them removes that memory driver, so
        # max_length can be raised safely below.
        nlp = spacy.load("en_core_web_sm", exclude=["parser", "ner"])
    except OSError as exc:  # pragma: no cover - exercised only without the model
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is not installed. "
            "Run: python -m spacy download en_core_web_sm"
        ) from exc
    # split_sentences() needs doc.sents, which this model normally derives
    # from the (now excluded) parser — a rule-based sentencizer replaces
    # that without pulling the parser's cost back in.
    nlp.add_pipe("sentencizer")
    nlp.max_length = 5_000_000
    return nlp


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


def simple_word_tokenize(text: str) -> list[str]:
    """Language-agnostic lowercase word extraction — no spaCy, no stopword
    removal. Used by LR2's frequent-words/alphabetic language-ID methods,
    which run on French text as well as English."""
    return [w.lower() for w in _UNICODE_WORD_RE.findall(text)]


def char_ngrams(text: str, n: int = 5) -> list[str]:
    """Word-boundary-padded character n-grams, e.g. char_ngrams("the", 5) -> [" the "]."""
    words = _WORD_RE.findall(text.lower())
    grams: list[str] = []
    for word in words:
        padded = f" {word} "
        for i in range(len(padded) - n + 1):
            grams.append(padded[i : i + n])
    return grams
