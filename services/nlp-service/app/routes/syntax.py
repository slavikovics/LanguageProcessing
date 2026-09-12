import asyncio

from fastapi import APIRouter
from nlp_core import syntax_parsing

from app.schemas.syntax import ParseSentenceRequest, ParseSentenceResponse, SyntaxTokenOut

router = APIRouter(tags=["syntax"])


@router.post("/syntax/parse", response_model=ParseSentenceResponse)
async def parse_sentence(payload: ParseSentenceRequest) -> ParseSentenceResponse:
    tokens = await asyncio.to_thread(syntax_parsing.parse_sentence, payload.text)
    return ParseSentenceResponse(tokens=[SyntaxTokenOut.model_validate(tok) for tok in tokens])
