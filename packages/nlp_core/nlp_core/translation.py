
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .tokenization import get_pipeline, tokenize

DictionaryLookup = dict[str, str]


def dictionary_key(lemma: str, pos: str | None) -> str:
    return f"{lemma.lower()}|{pos or '*'}"


def _lookup_translation(lookup: DictionaryLookup, lemma: str, pos: str) -> str | None:
    lemma = lemma.lower()
    return lookup.get(dictionary_key(lemma, pos)) or lookup.get(dictionary_key(lemma, None))


def _match_case(source: str, translation: str) -> str:
    if source.isupper() and len(source) > 1:
        return translation.upper()
    if source[:1].isupper():
        return translation[:1].upper() + translation[1:]
    return translation


@dataclass(frozen=True)
class TranslatedWord:
    lemma: str
    pos: str
    surface: str
    frequency: int
    translation: str | None


@dataclass(frozen=True)
class TranslationResult:
    translated_text: str
    word_count: int
    translated_word_count: int
    words: list[TranslatedWord] = field(default_factory=list)


def translate(text: str, lookup: DictionaryLookup) -> TranslationResult:
    """Word-for-word (direct/pословный) translation: every alphabetic token is
    looked up by (lemma, POS) — falling back to (lemma, any POS) — in the
    supplied dictionary and swapped in place; punctuation and whitespace are
    preserved exactly via spaCy's `whitespace_` so the output reads as normal
    text rather than a token list. Tokens without a dictionary entry are left
    untranslated (the direct-translation systems described in the assignment
    do not fall back to any other translation model)."""
    doc = get_pipeline()(text)

    rendered_parts: list[str] = []
    word_count = 0
    translated_word_count = 0
    frequency: Counter[tuple[str, str]] = Counter()
    surface_by_key: dict[tuple[str, str], str] = {}

    for tok in doc:
        if not tok.is_alpha:
            rendered_parts.append(tok.text_with_ws)
            continue

        word_count += 1
        lemma = tok.lemma_.lower()
        pos = tok.pos_
        translation = _lookup_translation(lookup, lemma, pos)

        if not tok.is_stop:
            key = (lemma, pos)
            frequency[key] += 1
            surface_by_key.setdefault(key, tok.text.lower())

        if translation:
            translated_word_count += 1
            rendered_parts.append(_match_case(tok.text, translation) + tok.whitespace_)
        else:
            rendered_parts.append(tok.text_with_ws)

    words = [
        TranslatedWord(
            lemma=lemma,
            pos=pos,
            surface=surface_by_key[(lemma, pos)],
            frequency=count,
            translation=_lookup_translation(lookup, lemma, pos),
        )
        for (lemma, pos), count in frequency.most_common()
    ]

    return TranslationResult(
        translated_text="".join(rendered_parts),
        word_count=word_count,
        translated_word_count=translated_word_count,
        words=words,
    )


def build_word_list(text: str, lookup: DictionaryLookup) -> list[TranslatedWord]:
    """Frequency-ordered word list with grammatical info and translations —
    tab 1 of the lab: reuses the same tokenize() as the LR1 frequency list,
    grouped by (lemma, POS) and sorted by descending frequency."""
    counts: Counter[tuple[str, str]] = Counter()
    surface_by_key: dict[tuple[str, str], str] = {}
    for tok in tokenize(text):
        key = (tok.lemma, tok.pos)
        counts[key] += 1
        surface_by_key.setdefault(key, tok.text)

    return [
        TranslatedWord(
            lemma=lemma,
            pos=pos,
            surface=surface_by_key[(lemma, pos)],
            frequency=count,
            translation=_lookup_translation(lookup, lemma, pos),
        )
        for (lemma, pos), count in counts.most_common()
    ]
