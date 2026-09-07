from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="Lang ID Service", version="0.1.0")
app.include_router(router)
