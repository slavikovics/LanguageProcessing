from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.interface.routers import (
    collections,
    crawl_jobs,
    crawl_seeds,
    documents,
    health,
    indexing,
    metrics,
    search,
    search_models,
)

settings = get_settings()

app = FastAPI(title="IR Lab API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(collections.router)
app.include_router(documents.router)
app.include_router(crawl_jobs.router)
app.include_router(crawl_seeds.router)
app.include_router(indexing.router)
app.include_router(search.router)
app.include_router(search_models.router)
app.include_router(metrics.router)
