from pydantic import BaseModel, ConfigDict


class TokenizeRequest(BaseModel):
    text: str
    keep_stopwords: bool = False


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str
    lemma: str
    pos: str
    is_stop: bool


class TokenizeResponse(BaseModel):
    tokens: list[TokenOut]


class LemmatizeRequest(BaseModel):
    text: str


class LemmatizeResponse(BaseModel):
    lemmas: list[str]


class LemmatizeBatchRequest(BaseModel):
    texts: list[str]


class LemmatizeBatchResponse(BaseModel):
    lemmas: list[list[str]]
