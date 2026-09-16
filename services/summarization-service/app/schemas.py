from pydantic import BaseModel


class SelectedSentence(BaseModel):
    index: int
    text: str
    weight: float


class SummarizeResponse(BaseModel):
    selected: list[SelectedSentence]
    total_sentences: int
    elapsed_ms: float


class AlgorithmicSummarizeRequest(BaseModel):
    text: str
    term_weights: dict[str, float]
    sentence_count: int = 10


class TextRankSummarizeRequest(BaseModel):
    text: str
    sentence_count: int = 10


class EmbeddingSummarizeRequest(BaseModel):
    sentences: list[str]
    embeddings: list[list[float]]
    sentence_count: int = 10
    query_embedding: list[float] | None = None


class KeywordGroup(BaseModel):
    term: str
    children: list[str]


class KeywordHierarchyRequest(BaseModel):
    text: str
    term_weights: dict[str, float]
    top_n: int | None = None
    max_children: int = 5


class KeywordHierarchyResponse(BaseModel):
    groups: list[KeywordGroup]
