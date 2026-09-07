from fastapi import FastAPI

from app.routes import embeddings, health, metrics, tokenization, weighting

app = FastAPI(title="NLP Service", version="0.1.0")
app.include_router(health.router)
app.include_router(tokenization.router)
app.include_router(weighting.router)
app.include_router(embeddings.router)
app.include_router(metrics.router)
