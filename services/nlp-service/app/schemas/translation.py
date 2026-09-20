from typing import Literal

from pydantic import BaseModel, ConfigDict


class TranslateRequest(BaseModel):
    text: str
    dictionary: dict[str, str]
    method: Literal["direct", "transfer", "neural"] = "direct"


class TranslatedWordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lemma: str
    pos: str
    surface: str
    frequency: int
    translation: str | None


class DiffSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str
    changed: bool


class TranslateResponse(BaseModel):
    translated_text: str
    word_count: int
    translated_word_count: int
    words: list[TranslatedWordOut]
    diff_segments: list[DiffSegmentOut] = []


class WordListRequest(BaseModel):
    text: str
    dictionary: dict[str, str]


class WordListResponse(BaseModel):
    words: list[TranslatedWordOut]
