import json
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.rate_limit import limiter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import conversation_service, llm_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute;100/hour")
async def chat(request: Request, body: ChatRequest):
    session_id = conversation_service.get_or_create_session(body.session_id)
    history = conversation_service.get_history(session_id)

    try:
        reply = await llm_service.generate_response(body.message, history)
    except Exception as e:
        logger.error("LLM error: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Unable to generate a response right now. Please try again.",
        )

    conversation_service.add_exchange(session_id, body.message, reply)
    return ChatResponse(response=reply, session_id=session_id)


@router.post("/stream")
@limiter.limit("20/minute;100/hour")
async def chat_stream(request: Request, body: ChatRequest):
    session_id = conversation_service.get_or_create_session(body.session_id)
    history = conversation_service.get_history(session_id)

    full_parts: list[str] = []

    async def event_generator():
        try:
            async for chunk in llm_service.stream_response(body.message, history):
                full_parts.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # Persist exchange after streaming completes
            conversation_service.add_exchange(
                session_id, body.message, "".join(full_parts)
            )
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

        except Exception as e:
            logger.error("Streaming error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Unable to generate a response right now.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
