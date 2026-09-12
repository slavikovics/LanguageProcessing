from pydantic import BaseModel, ConfigDict


class ParseSentenceRequest(BaseModel):
    text: str


class SyntaxTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    text: str
    lemma: str
    pos: str
    dep: str
    head_position: int | None
    head_text: str | None
    morph: dict[str, str]
    is_punct: bool


class ParseSentenceResponse(BaseModel):
    tokens: list[SyntaxTokenOut]
