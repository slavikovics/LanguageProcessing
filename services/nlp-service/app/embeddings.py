"""Dense-embedding encoding for the second ("gte-multilingual-base") search
model. Kept in nlp-service rather than packages/nlp_core: it pulls in
torch/sentence-transformers, real ML dependencies that nlp_core must stay
free of since other course labs reuse that package and don't need them.

No chunking: gte-multilingual-base's 8192-token context covers virtually
every crawled document whole. sentence-transformers' own tokenizer
truncation acts as a safety cap for the rare oversized outlier — that is a
length cap, not chunking, and needs no chunk-to-document mapping table.
"""

from __future__ import annotations

from functools import lru_cache

MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"
NATIVE_DIM = 768


def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, trust_remote_code=True, device="cpu")


@lru_cache(maxsize=1)
def get_model():
    """Lazily load and cache the embedding model — mirrors
    nlp_core.tokenization.get_pipeline()'s lazy-singleton pattern."""
    return _load_model()


def encode_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_model()
    vectors = model.encode(texts, batch_size=8, show_progress_bar=False, normalize_embeddings=True)
    return vectors.tolist()


def encode_query(text: str) -> list[float]:
    return encode_documents([text])[0]
