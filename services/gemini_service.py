"""
services/gemini_service.py
--------------------------
All Gemini API interactions live here.  No other file imports google.generativeai.

Responsibilities
----------------
- Configure the Gemini client once at import time.
- Expose two simple functions:
    chat_with_tools()  — runs the agentic tool-calling loop for /chat
    explain_alert()    — single-shot call that explains one alert
- Keep prompts here (or import from a prompts dict) so they're easy to iterate.

To swap providers later: rewrite only this file.
"""

from __future__ import annotations
import json
import logging
from typing import Any

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client init — happens once when the module is first imported
# ---------------------------------------------------------------------------

def _init_client() -> None:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured. Check your .env file.")
    genai.configure(api_key=settings.GEMINI_API_KEY)

_init_client()

# ---------------------------------------------------------------------------
# Tool declarations (schema only — actual execution is in agent_tools.py)
# ---------------------------------------------------------------------------

_TOOL_DECLARATIONS = Tool(function_declarations=[
    FunctionDeclaration(
        name="get_current_stock",
        description=(
            "Fetch the current fuel stock levels and prices for one or all stations. "
            "Use this when the operator asks about current stock, fuel levels, "
            "or how much fuel is available right now."
        ),
        parameters={
            "type": "object",
            "properties": {
                "station_id": {
                    "type": "string",
                    "description": "Optional station ID to filter results (e.g. 'AGIL-001'). "
                                   "Omit to get all stations.",
                },
            },
        },
    ),
    FunctionDeclaration(
        name="get_fuel_history",
        description=(
            "Fetch historical fuel consumption and stock data for a station. "
            "Use this when the operator asks about trends, past usage, or "
            "consumption patterns over time."
        ),
        parameters={
            "type": "object",
            "properties": {
                "station_id": {
                    "type": "string",
                    "description": "Station ID to retrieve history for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of records to return (default 20).",
                },
            },
        },
    ),
    FunctionDeclaration(
        name="get_alerts",
        description=(
            "Fetch active alerts for one or all stations. "
            "Use this when the operator asks about warnings, problems, "
            "critical conditions, or anything that needs attention."
        ),
        parameters={
            "type": "object",
            "properties": {
                "station_id": {
                    "type": "string",
                    "description": "Optional station ID. Omit for all stations.",
                },
            },
        },
    ),
])

# ---------------------------------------------------------------------------
# System prompt for the conversational agent
# ---------------------------------------------------------------------------

_CHAT_SYSTEM_PROMPT = """
You are a helpful fuel station operations assistant for the AGIL fuel station network.
You have access to real-time tools to fetch current stock levels, fuel history, and alerts.

Guidelines:
- Always use the appropriate tool to fetch data before answering questions about stock or alerts.
- Give concise, actionable answers in plain language.
- When stock is low, proactively mention it and suggest reordering.
- If you are unsure, say so — do not fabricate numbers.
- Format numbers clearly: use L for liters, DT for Dinar.
- Respond in the same language the operator uses (French or English).
""".strip()

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chat_with_tools(
    user_message: str,
    history: list[dict],
    tool_executor,         # callable: (name: str, args: dict) -> Any
) -> tuple[str, list[str]]:
    """
    Run a multi-turn Gemini tool-calling loop.

    Parameters
    ----------
    user_message  : The latest user turn.
    history       : Previous turns as list of {"role": ..., "content": ...}.
    tool_executor : A callable that receives (tool_name, tool_args) and returns
                    the result.  Injected from agent_tools.py — keeps this file
                    decoupled from HTTP/mock logic.

    Returns
    -------
    (answer_text, sources_used)
    answer_text  : Final plain-language reply to show the operator.
    sources_used : List of tool names that were called during reasoning.
    """
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=_CHAT_SYSTEM_PROMPT,
        tools=[_TOOL_DECLARATIONS],
    )

    # Build Gemini-format history from our schema
    gemini_history = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [turn["content"]]})

    chat = model.start_chat(history=gemini_history)
    sources_used: list[str] = []

    # Send the new user message
    response = chat.send_message(user_message)

    # Agentic loop: keep processing tool calls until the model returns text
    MAX_ITERATIONS = 5
    for _ in range(MAX_ITERATIONS):
        # Check if there are any function calls in the response
        function_calls = []
        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                function_calls.append(part.function_call)

        if not function_calls:
            # Model returned a final text answer — we're done
            break

        # Execute each tool call and collect results
        tool_results = []
        for fc in function_calls:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            logger.info("Tool call: %s(%s)", tool_name, tool_args)

            if tool_name not in sources_used:
                sources_used.append(tool_name)

            try:
                result = tool_executor(tool_name, tool_args)
            except Exception as exc:
                result = {"error": str(exc)}

            tool_results.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=tool_name,
                        response={"result": json.dumps(result, default=str)},
                    )
                )
            )

        # Feed tool results back to the model
        response = chat.send_message(tool_results)

    # Extract final text
    final_text = ""
    for part in response.parts:
        if hasattr(part, "text") and part.text:
            final_text += part.text

    if not final_text:
        final_text = "I was unable to generate a response. Please try again."

    return final_text, sources_used


def explain_alert(alert: dict) -> tuple[str, str]:
    """
    Generate a plain-English explanation and recommended action for one alert.

    Parameters
    ----------
    alert : A single alert dict (matching AlertResponse schema minus explanation fields).

    Returns
    -------
    (explanation, recommended_action)
    """
    model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)

    prompt = f"""
You are a fuel station operations expert.

Given this alert, write:
1. A plain-English explanation (1-2 sentences) of what is happening and why it matters.
2. A concrete recommended action (1 sentence) for the station operator.

Alert details:
- Station: {alert.get('station_id')}
- Fuel type: {alert.get('fuel_type')}
- Alert type: {alert.get('alert_type')}
- Severity: {alert.get('severity')}
- Message: {alert.get('message')}

Respond ONLY as valid JSON with exactly these two keys:
{{"explanation": "...", "recommended_action": "..."}}
""".strip()

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return data.get("explanation", ""), data.get("recommended_action", "")
    except Exception as exc:
        logger.warning("explain_alert failed for alert %s: %s", alert.get("id"), exc)
        return "Unable to generate explanation.", "Please review this alert manually."
