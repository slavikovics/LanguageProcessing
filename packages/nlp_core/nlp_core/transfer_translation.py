
from __future__ import annotations

import difflib
import re
from collections import Counter
from dataclasses import dataclass

from . import fr_morphology
from .syntax_parsing import get_parser_pipeline
from .translation import (
    DictionaryLookup,
    DiffSegment,
    TranslatedWord,
    TranslationResult,
    _build_word_list,
    _lookup_translation,
    _match_case,
    _record_word_frequency,
    translate as _direct_translate,
)

_PRENOMINAL_ADJECTIVES = frozenset(
    {
        "beautiful", "good", "bad", "big", "small", "young", "old", "new",
        "pretty", "great", "little", "high", "long", "short", "nice", "fine",
    }
)

_CONTRACTIONS = {
    ("de", "le"): "du",
    ("de", "les"): "des",
    ("à", "le"): "au",
    ("à", "les"): "aux",
}

_VOWEL_SOUND = set("aeiouyàâäéèêëîïôöùûüh")
_ALWAYS_NO_SPACE_BEFORE = set(".,;:!?)]}")


@dataclass(frozen=True)
class _Token:
    i: int
    text: str
    lemma: str
    pos: str
    dep: str
    head_i: int
    is_alpha: bool
    is_punct: bool
    is_stop: bool
    sent_id: int
    no_space_before: bool
    morph: dict[str, str]
    is_sent_start: bool


@dataclass
class _Unit:
    token: _Token | None = None
    literal_text: str | None = None
    literal_sent_id: int = 0
    forced_translation: str | None = None

    @property
    def sent_id(self) -> int:
        return self.token.sent_id if self.token is not None else self.literal_sent_id


def _analyze(text: str) -> tuple[list[_Token], dict[int, _Token]]:
    doc = get_parser_pipeline()(text)
    tokens: list[_Token] = []
    sent_id = -1
    prev_had_trailing_space = True
    for tok in doc:
        if tok.is_space:
            prev_had_trailing_space = True
            continue
        if tok.is_sent_start:
            sent_id += 1
        tokens.append(
            _Token(
                i=tok.i,
                text=tok.text,
                lemma=tok.lemma_.lower(),
                pos=tok.pos_,
                dep=tok.dep_,
                head_i=tok.head.i,
                is_alpha=tok.is_alpha,
                is_punct=tok.is_punct,
                is_stop=tok.is_stop,
                sent_id=max(sent_id, 0),
                no_space_before=not prev_had_trailing_space,
                morph=tok.morph.to_dict() if tok.morph else {},
                is_sent_start=tok.is_sent_start,
            )
        )
        prev_had_trailing_space = bool(tok.whitespace_)
    return tokens, {tok.i: tok for tok in tokens}


def _index_of(units: list[_Unit], token_i: int) -> int | None:
    return next((idx for idx, u in enumerate(units) if u.token is not None and u.token.i == token_i), None)


def _apply_negation(
    units: list[_Unit], tokens_by_i: dict[int, _Token], lookup: DictionaryLookup
) -> list[_Unit]:
    result = list(units)
    neg_token_ids = [u.token.i for u in result if u.token is not None and u.token.dep == "neg"]

    for neg_i in neg_token_ids:
        neg_idx = _index_of(result, neg_i)
        if neg_idx is None:
            continue
        head = tokens_by_i.get(result[neg_idx].token.head_i)
        if head is None:
            continue

        aux_i = next(
            (
                t.i
                for t in tokens_by_i.values()
                if t.head_i == head.i and t.dep == "aux" and t.lemma == "do"
            ),
            None,
        )
        aux_idx = _index_of(result, aux_i) if aux_i is not None else None

        for idx in sorted({neg_idx, aux_idx} - {None}, reverse=True):
            del result[idx]

        head_idx = _index_of(result, head.i)
        if head_idx is None:
            continue
        result.insert(head_idx + 1, _Unit(literal_text="pas", literal_sent_id=head.sent_id))
        result.insert(head_idx, _Unit(literal_text="ne", literal_sent_id=head.sent_id))

    return result


def _apply_adjective_postposition(
    units: list[_Unit], tokens_by_i: dict[int, _Token], lookup: DictionaryLookup
) -> list[_Unit]:
    result = list(units)
    candidates = [
        u.token
        for u in result
        if u.token is not None
        and u.token.dep == "amod"
        and u.token.lemma not in _PRENOMINAL_ADJECTIVES
    ]

    for adj in candidates:
        head = tokens_by_i.get(adj.head_i)
        if head is None or head.pos not in {"NOUN", "PROPN"} or adj.i >= head.i:
            continue
        adj_idx = _index_of(result, adj.i)
        if adj_idx is None:
            continue
        del result[adj_idx]

        head_idx = _index_of(result, head.i)
        if head_idx is None:
            continue
        insert_at = head_idx + 1
        while (
            insert_at < len(result)
            and result[insert_at].token is not None
            and result[insert_at].token.dep == "amod"
            and result[insert_at].token.head_i == head.i
        ):
            insert_at += 1
        result.insert(insert_at, _Unit(token=adj))

    return result


def _apply_morphological_agreement(
    units: list[_Unit], tokens_by_i: dict[int, _Token], lookup: DictionaryLookup
) -> list[_Unit]:
    for unit in units:
        if unit.token is None:
            continue
        tok = unit.token

        if tok.dep == "amod":
            head = tokens_by_i.get(tok.head_i)
            if head is None:
                continue
            adj_base = _lookup_translation(lookup, tok.lemma, tok.pos)
            head_translation = _lookup_translation(lookup, head.lemma, head.pos)
            if adj_base is None or head_translation is None:
                continue
            gender = fr_morphology.guess_gender(head_translation)
            number = head.morph.get("Number") or tok.morph.get("Number")
            unit.forced_translation = fr_morphology.agree_adjective(adj_base, gender, number)

        elif tok.pos == "VERB":
            verb_base = _lookup_translation(lookup, tok.lemma, tok.pos)
            if verb_base is None:
                continue
            person = tok.morph.get("Person")
            number = tok.morph.get("Number")
            unit.forced_translation = fr_morphology.conjugate_verb(verb_base, person, number)

        elif tok.pos in {"NOUN", "PROPN"} and tok.morph.get("Number") == "Plur":
            noun_base = _lookup_translation(lookup, tok.lemma, tok.pos)
            if noun_base is None:
                continue
            unit.forced_translation = fr_morphology.pluralize_noun(noun_base)

    return units


_TRANSFER_RULES = (_apply_negation, _apply_adjective_postposition, _apply_morphological_agreement)

_TOKEN_OR_SPACE = re.compile(r"\S+|\s+")


def _diff_against_direct(direct_text: str, transfer_text: str) -> list[DiffSegment]:
    transfer_tokens = _TOKEN_OR_SPACE.findall(transfer_text)
    direct_words = re.findall(r"\S+", direct_text)
    word_indices = [i for i, tok in enumerate(transfer_tokens) if not tok.isspace()]
    transfer_words = [transfer_tokens[i] for i in word_indices]

    changed_words = [False] * len(transfer_words)
    matcher = difflib.SequenceMatcher(a=direct_words, b=transfer_words, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            for j in range(j1, j2):
                changed_words[j] = True
    changed_by_token_index = dict(zip(word_indices, changed_words))

    segments: list[DiffSegment] = []
    for idx, token in enumerate(transfer_tokens):
        changed = changed_by_token_index.get(idx, False)
        if segments and segments[-1].changed == changed:
            segments[-1] = DiffSegment(text=segments[-1].text + token, changed=changed)
        else:
            segments.append(DiffSegment(text=token, changed=changed))
    return segments


_Rendered = tuple[str, int, bool, bool]


def _case_source(tok: _Token) -> str:
    if tok.is_sent_start and not (tok.text.isupper() and len(tok.text) > 1):
        return tok.text.lower()
    return tok.text


def _render_units(units: list[_Unit], lookup: DictionaryLookup) -> list[_Rendered]:
    rendered: list[_Rendered] = []
    prev_token_i: int | None = None
    for unit in units:
        if unit.token is None:
            rendered.append((unit.literal_text, unit.literal_sent_id, False, False))
            prev_token_i = None
            continue
        tok = unit.token
        still_adjacent = prev_token_i is not None and tok.i == prev_token_i + 1
        no_space_before = still_adjacent and tok.no_space_before
        if not tok.is_alpha:
            no_space_before = no_space_before or tok.text in _ALWAYS_NO_SPACE_BEFORE
            rendered.append((tok.text, tok.sent_id, True, no_space_before))
        else:
            translation = unit.forced_translation or _lookup_translation(lookup, tok.lemma, tok.pos)
            case_source = _case_source(tok)
            surface = _match_case(case_source, translation) if translation else case_source
            rendered.append((surface, tok.sent_id, False, no_space_before))
        prev_token_i = tok.i
    return rendered


def _apply_contractions(rendered: list[_Rendered]) -> list[_Rendered]:
    result: list[_Rendered] = []
    i = 0
    while i < len(rendered):
        if i + 1 < len(rendered):
            a_text, a_sent, a_punct, a_no_space_before = rendered[i]
            b_text, _b_sent, b_punct, _b_no_space_before = rendered[i + 1]
            key = (a_text.lower(), b_text.lower())
            if not a_punct and not b_punct and key in _CONTRACTIONS:
                result.append((_match_case(a_text, _CONTRACTIONS[key]), a_sent, False, a_no_space_before))
                i += 2
                continue
        result.append(rendered[i])
        i += 1
    return result


def _apply_elision(rendered: list[_Rendered]) -> list[_Rendered]:
    result: list[_Rendered] = []
    for idx, (text, sent_id, is_punct, no_space_before) in enumerate(rendered):
        if text.lower() == "ne" and idx + 1 < len(rendered) and rendered[idx + 1][0][:1].lower() in _VOWEL_SOUND:
            result.append(("N'" if text[:1].isupper() else "n'", sent_id, is_punct, no_space_before))
            continue
        result.append((text, sent_id, is_punct, no_space_before))
    return result


def _join(rendered: list[_Rendered]) -> str:
    parts: list[str] = []
    prev_sent_id: int | None = None
    prev_no_space_after = False

    for text, sent_id, _is_punct, no_space_before in rendered:
        if sent_id != prev_sent_id and text:
            text = text[:1].upper() + text[1:]
        needs_space = bool(parts) and not prev_no_space_after and not no_space_before
        if needs_space:
            parts.append(" ")
        parts.append(text)
        prev_sent_id = sent_id
        prev_no_space_after = text.endswith("'")

    return "".join(parts)


def transfer_translate(text: str, lookup: DictionaryLookup) -> TranslationResult:
    tokens, tokens_by_i = _analyze(text)

    word_count = 0
    translated_word_count = 0
    frequency: Counter[tuple[str, str]] = Counter()
    surface_by_key: dict[tuple[str, str], str] = {}

    for tok in tokens:
        if not tok.is_alpha:
            continue
        word_count += 1
        if not tok.is_stop:
            _record_word_frequency(tok.lemma, tok.pos, tok.text.lower(), frequency, surface_by_key)
        if _lookup_translation(lookup, tok.lemma, tok.pos):
            translated_word_count += 1

    words = _build_word_list(frequency, surface_by_key, lookup)

    units = [_Unit(token=tok) for tok in tokens]
    for rule in _TRANSFER_RULES:
        units = rule(units, tokens_by_i, lookup)

    rendered = _render_units(units, lookup)
    rendered = _apply_contractions(rendered)
    rendered = _apply_elision(rendered)
    translated_text = _join(rendered)

    direct_text = _direct_translate(text, lookup).translated_text
    diff_segments = _diff_against_direct(direct_text, translated_text)

    return TranslationResult(
        translated_text=translated_text,
        word_count=word_count,
        translated_word_count=translated_word_count,
        words=words,
        diff_segments=diff_segments,
    )
