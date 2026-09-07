from pydantic import BaseModel


class IdfRequest(BaseModel):
    document_term_lists: list[list[str]]


class IdfResponse(BaseModel):
    total_documents: int
    document_frequency: dict[str, int]
    idf: dict[str, float]


class DocumentVectorRequest(BaseModel):
    term_frequencies: dict[str, int]
    idf: dict[str, float]


class VectorResponse(BaseModel):
    vector: dict[str, float]


class QueryVectorRequest(BaseModel):
    terms: list[str]


class SimilarityRequest(BaseModel):
    a: dict[str, float]
    b: dict[str, float]


class SimilarityResponse(BaseModel):
    score: float


class IndexRequest(BaseModel):
    document_term_lists: list[list[str]]


class IndexResponse(BaseModel):
    idf: dict[str, float]
    term_frequencies: list[dict[str, int]]
    vectors: list[dict[str, float]]


class IdfFromFrequencyRequest(BaseModel):
    document_frequency: dict[str, int]
    total_documents: int


class IdfFromFrequencyResponse(BaseModel):
    idf: dict[str, float]
