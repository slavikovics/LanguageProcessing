import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.model import warmup
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(asyncio.to_thread(warmup))
    yield


app = FastAPI(title="MT Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)
