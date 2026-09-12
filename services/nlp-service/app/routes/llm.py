from fastapi import APIRouter

from app import llm
from app.schemas.llm import PolishRequest, PolishResponse

router = APIRouter(tags=["nlp"])


@router.post("/llm/polish", response_model=PolishResponse)
async def polish(payload: PolishRequest) -> PolishResponse:
    polished_markdown = await llm.polish(payload.text, language=payload.language)
    return PolishResponse(polished_markdown=polished_markdown, model=llm.MODEL_NAME)
