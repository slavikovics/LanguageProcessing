import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import router
from app.stt_local import warmup


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fire-and-forget: runs the (blocking) model load in a worker thread
    # instead of awaiting it here, so the container reports ready and starts
    # accepting requests immediately rather than waiting out the load first.
    # See stt_local.warmup for why this matters for the live-stream gateway.
    asyncio.create_task(asyncio.to_thread(warmup))
    yield


app = FastAPI(title="Speech Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)
