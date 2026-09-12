from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="Summarization Service", version="0.1.0")
app.include_router(router)
