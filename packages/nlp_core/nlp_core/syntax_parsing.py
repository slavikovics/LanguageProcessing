
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class SyntaxToken:
    position: int
    text: str
    lemma: str
    pos: str
    dep: str
    head_position: int | None
    head_text: str | None
    morph: dict[str, str]
    is_punct: bool


def _load_parser_pipeline():
    import spacy

    try:
        nlp = spacy.load("en_core_web_sm", exclude=["ner"])
    except OSError as exc:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is not installed. "
            "Run: python -m spacy download en_core_web_sm"
        ) from exc
    nlp.max_length = 5_000_000
    return nlp


@lru_cache(maxsize=1)
def get_parser_pipeline():
    return _load_parser_pipeline()


def parse_sentence(text: str) -> list[SyntaxToken]:
    doc = get_parser_pipeline()(text)
    return [
        SyntaxToken(
            position=tok.i,
            text=tok.text,
            lemma=tok.lemma_.lower(),
            pos=tok.pos_,
            dep=tok.dep_,
            head_position=tok.head.i if tok.head != tok else None,
            head_text=tok.head.text if tok.head != tok else None,
            morph=tok.morph.to_dict() if tok.morph else {},
            is_punct=tok.is_punct,
        )
        for tok in doc
        if not tok.is_space
    ]
