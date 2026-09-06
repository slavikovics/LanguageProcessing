from pydantic import BaseModel, ConfigDict


class TokenizeRequest(BaseModel):
    text: str
    keep_stopwords: bool = False


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # nlp_core.tokenization.Token is a dataclass

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


class LemmatizeBatchRequest(BaseModel):
    texts: list[str]


class LemmatizeBatchResponse(BaseModel):
    lemmas: list[list[str]]


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


class MetricsEvaluateRequest(BaseModel):
    ranked_ids: list[int]
    relevant_ids: list[int]


class MetricsEvaluateResponse(BaseModel):
    """Rank-quality metrics for one query. Whole-list Precision/Recall/F1 are
    omitted — this system always ranks the full collection, so they'd
    degenerate (Recall≡1, Precision≈relevant/collection_size). The @5/@10
    cutoff variants below stay meaningful instead."""

    retrieved_count: int
    relevant_count: int
    precision_at_5: float
    precision_at_10: float
    recall_at_5: float
    recall_at_10: float
    f1_at_5: float
    f1_at_10: float
    average_precision: float
    r_precision: float
    curve: list[tuple[float, float]]


class EmbedDocumentsRequest(BaseModel):
    texts: list[str]


class EmbedDocumentsResponse(BaseModel):
    vectors: list[list[float]]


class EmbedQueryRequest(BaseModel):
    text: str


class EmbedQueryResponse(BaseModel):
    vector: list[float]
