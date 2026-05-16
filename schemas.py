"""
schemas.py
----------
All request/response Pydantic models for  microservice.

API contract agreed with (Angular frontend):

POST /chat
  Request:  ChatRequest
  Response: ChatResponse

GET /alerts
  Response: list[AlertResponse]
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /chat  contract
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single turn in the conversation (role: 'user' or 'assistant')."""
    role: str = Field(..., examples=["user", "assistant"])
    content: str


class ChatRequest(BaseModel):
    """
    Body sent by the Angular ChatService on every turn.

    Fields
    ------
    message     : The new user message (current turn).
    history     : All previous turns, oldest first.
                  Angular must accumulate and re-send this on each request.
    session_id  : Optional client-generated ID for logging/tracing.
    station_id  : Optional — scopes tool calls to a specific station.
    """
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    session_id: Optional[str] = None
    station_id: Optional[str] = None


class ChatResponse(BaseModel):
    """
    Response returned to Angular after the agent finishes reasoning.

    Fields
    ------
    response    : Plain-language answer to display in the chat thread.
    session_id  : Echoed back so Angular can correlate requests.
    sources_used: Which backend tools were called (for transparency).
    """
    response: str
    session_id: Optional[str] = None
    sources_used: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /alerts  contract  (extends the main project's AlertResponse)
# ---------------------------------------------------------------------------

class AlertResponse(BaseModel):
    """
    Alert record enriched with an LLM-generated explanation.

    The `explanation` field is NEW —  just starts rendering it.
    All other fields mirror the main project's AlertResponse schema so
    the Angular AlertService needs zero changes to its existing parsing.
    """
    id: int
    station_id: str
    fuel_type: str
    alert_type: str
    severity: str                              # "low" | "medium" | "high" | "critical"
    message: str
    timestamp: str
    explanation: Optional[str] = None          # ← NEW: LLM plain-English explanation
    recommended_action: Optional[str] = None   # ← NEW: LLM suggested next step
