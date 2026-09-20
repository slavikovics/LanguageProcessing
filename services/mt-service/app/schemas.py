from pydantic import BaseModel


class TranslateRequest(BaseModel):
    sentences: list[str]


class TranslateResponse(BaseModel):
    translations: list[str]
