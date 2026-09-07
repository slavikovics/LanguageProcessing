from pydantic import BaseModel


class FrequentWordsProfileRequest(BaseModel):
    texts: list[str]
    top_n: int = 300


class FrequentWordsProfileResponse(BaseModel):
    top_words: list[str]


class FrequentWordsIdentifyRequest(BaseModel):
    top_words_by_language: dict[str, list[str]]
    text: str


class IdentifyResponse(BaseModel):
    distances: dict[str, float]
    predicted_language: str
    elapsed_ms: float


class AlphabeticProfileRequest(BaseModel):
    texts: list[str]


class AlphabeticProfileResponse(BaseModel):
    frequencies: dict[str, float]


class AlphabeticIdentifyRequest(BaseModel):
    profiles_by_language: dict[str, dict[str, float]]
    text: str


class NeuralTrainStepRequest(BaseModel):
    vectors_by_language: dict[str, list[list[float]]]
    weights: list[list[float]] | None = None
    bias: list[float] | None = None
    classes: list[str] | None = None
    epochs: int = 10
    learning_rate: float = 0.01
    weight_decay: float = 1e-3


class NeuralTrainStepResponse(BaseModel):
    weights: list[list[float]]
    bias: list[float]
    classes: list[str]
    loss_curve_chunk: list[float]
    train_accuracy: float


class NeuralIdentifyRequest(BaseModel):
    weights: list[list[float]]
    bias: list[float]
    classes: list[str]
    vector: list[float]


class NeuralIdentifyResponse(BaseModel):
    distances: dict[str, float]
    probabilities: dict[str, float]
    predicted_language: str
    elapsed_ms: float
