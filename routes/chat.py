"""
routes/chat.py
--------------
POST /chat  — Conversational Q&A agent endpoint.

Flow
----
1. Angular sends { message, history, session_id, station_id }.
2. We pass history + message into gemini_service.chat_with_tools().
3. Gemini reasons and calls tools (get_current_stock, get_fuel_history, get_alerts).
4. agent_tools.execute_tool() fetches the data (real or mock).
5. Gemini synthesises a plain-language answer.
6. We return { response, session_id, sources_used }.

The Angular ChatService accumulates history client-side and re-sends it
with every request so the backend agent always has full context.
"""

import logging
from fastapi import APIRouter, HTTPException

from schemas import ChatRequest, ChatResponse
from services import gemini_service, agent_tools

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse, tags=["Chat Agent"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Conversational Q&A agent.

    Send a user message and conversation history; receive a plain-language
    answer synthesised from live fuel station data.
    """
    logger.info(
        "Chat request | session=%s | station=%s | message=%r",
        request.session_id,
        request.station_id,
        request.message[:80],
    )

    # Convert Pydantic history to plain dicts for gemini_service
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

    # If a station_id is provided, inject it into the first user message as context
    augmented_message = request.message
    if request.station_id:
        augmented_message = (
            f"[Context: the operator is viewing station {request.station_id}]\n"
            f"{request.message}"
        )

    try:
        answer, sources_used = gemini_service.chat_with_tools(
            user_message=augmented_message,
            history=history_dicts,
            tool_executor=agent_tools.execute_tool,
        )
    except Exception as exc:
        logger.exception("chat_with_tools failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="The AI agent encountered an error. Please try again.",
        )

    return ChatResponse(
        response=answer,
        session_id=request.session_id,
        sources_used=sources_used,
    )
