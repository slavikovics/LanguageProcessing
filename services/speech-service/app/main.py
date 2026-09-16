import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import router
from app.stt_local import warmup


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fire-and-forget: don't block startup on model load; see stt_local.warmup.
    asyncio.create_task(asyncio.to_thread(warmup))
    yield


app = FastAPI(title="Speech Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)
