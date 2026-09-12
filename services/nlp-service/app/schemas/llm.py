from pydantic import BaseModel


class PolishRequest(BaseModel):
    text: str
    language: str | None = None


class PolishResponse(BaseModel):
    polished_markdown: str
    model: str
