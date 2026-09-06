"""Dense-embedding encoding for the second ("multilingual-e5-small") search
model. Kept in nlp-service rather than packages/nlp_core: it pulls in
torch/sentence-transformers, real ML dependencies that nlp_core must stay
free of since other course labs reuse that package and don't need them.

Replaced Alibaba GTE Multilingual Base (768-dim, 8192-token context): on
CPU, per-document encode time scales with input length, and whole-document
encoding at that context size measured multiple seconds per long crawled
page — dominating indexing time for any collection with a handful of long
articles. multilingual-e5-small has a 512-token context (tens of times
faster per call) — the api service's indexing pipeline compensates for the
smaller window by chunking long documents and encoding each chunk instead
of the whole text (see app.domain.indexing.chunk_text in the api service),
so no document content is silently dropped, just split across more vectors.
"""

from __future__ import annotations

from functools import lru_cache

MODEL_NAME = "intfloat/multilingual-e5-small"
NATIVE_DIM = 384

# E5 models are trained with asymmetric instruction prefixes: text being
# indexed is prefixed "passage: ", text being searched for is prefixed
# "query: " — the model card documents this as required for good retrieval
# quality, even though nothing else about encoding differs between the two.
_PASSAGE_PREFIX = "passage: "
_QUERY_PREFIX = "query: "


def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, device="cpu")


@lru_cache(maxsize=1)
def get_model():
    """Lazily load and cache the embedding model — mirrors
    nlp_core.tokenization.get_pipeline()'s lazy-singleton pattern."""
    return _load_model()


def encode_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_model()
    vectors = model.encode(
        [_PASSAGE_PREFIX + text for text in texts],
        batch_size=8,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return vectors.tolist()


def encode_query(text: str) -> list[float]:
    model = get_model()
    vector = model.encode(_QUERY_PREFIX + text, show_progress_bar=False, normalize_embeddings=True)
    return vector.tolist()
