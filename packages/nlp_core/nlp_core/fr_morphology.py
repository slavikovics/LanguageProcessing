
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def _load_noun_forms() -> dict[str, tuple[str, str | None]]:
    forms: dict[str, tuple[str, str | None]] = {}
    path = _DATA_DIR / "fr_noun_forms.tsv"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                word, gender, plural = line.rstrip("\n").split("\t")
                forms[word] = (gender, plural or None)
    return forms


@lru_cache(maxsize=1)
def _load_adjective_forms() -> dict[str, dict[str, str]]:
    forms: dict[str, dict[str, str]] = {}
    path = _DATA_DIR / "fr_adjective_forms.tsv"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                ms, fs, mp, fp = line.rstrip("\n").split("\t")
                forms[ms] = {"ms": ms, "fs": fs or ms, "mp": mp or ms, "fp": fp or fs or ms}
    return forms


@lru_cache(maxsize=1)
def _load_verb_forms() -> dict[str, dict[str, str]]:
    forms: dict[str, dict[str, str]] = {}
    path = _DATA_DIR / "fr_verb_forms.tsv"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                infinitive, p1s, p2s, p3s, p1p, p2p, p3p = line.rstrip("\n").split("\t")
                forms[infinitive] = {
                    "1_Sing": p1s or infinitive,
                    "2_Sing": p2s or infinitive,
                    "3_Sing": p3s or infinitive,
                    "1_Plur": p1p or infinitive,
                    "2_Plur": p2p or infinitive,
                    "3_Plur": p3p or infinitive,
                }
    return forms


def guess_gender(word: str) -> str:
    entry = _load_noun_forms().get(word.lower().strip())
    return entry[0] if entry is not None else "m"


def agree_adjective(base: str, gender: str | None, number: str | None) -> str:
    base = base.lower().strip()
    forms = _load_adjective_forms().get(base)
    if forms is None:
        return base
    slot = ("f" if gender == "f" else "m") + ("p" if number == "Plur" else "s")
    return forms[slot]


def pluralize_noun(base: str) -> str:
    base = base.lower().strip()
    entry = _load_noun_forms().get(base)
    if entry is not None and entry[1]:
        return entry[1]
    return base


def conjugate_verb(infinitive: str, person: str | None, number: str | None) -> str:
    infinitive = infinitive.lower().strip()
    forms = _load_verb_forms().get(infinitive)
    if forms is None:
        return infinitive
    key = f"{person or '3'}_{number or 'Sing'}"
    return forms.get(key, infinitive)
