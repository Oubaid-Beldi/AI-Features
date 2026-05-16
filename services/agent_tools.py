"""
services/agent_tools.py
-----------------------
The "hands" of the conversational agent.

When Gemini calls a tool (get_current_stock, get_fuel_history, get_alerts),
this module executes it by either:
  - Calling the real backend over HTTP  (BACKEND_MODE=real)
  - Returning mock data                 (BACKEND_MODE=mock)

This is the ONLY place where the choice between real/mock matters.
gemini_service.py doesn't know the difference — it just calls execute_tool().
"""

from __future__ import annotations
import logging
from typing import Any

import httpx

from config import settings
from mocks import backend_mock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP helpers (used only when BACKEND_MODE=real)
# ---------------------------------------------------------------------------

def _get(path: str, params: dict | None = None) -> Any:
    """Make a GET request to the main backend. Raises on failure."""
    url = f"{settings.BACKEND_URL}{path}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_get_current_stock(station_id: str | None = None) -> Any:
    if settings.is_mock():
        return backend_mock.get_current(station_id)
    params = {"station_id": station_id} if station_id else {}
    return _get("/current", params)


def _tool_get_fuel_history(station_id: str | None = None, limit: int = 20) -> Any:
    if settings.is_mock():
        return backend_mock.get_history(station_id, limit)
    params = {"limit": limit}
    if station_id:
        params["station_id"] = station_id
    return _get("/history", params)


def _tool_get_alerts(station_id: str | None = None) -> Any:
    if settings.is_mock():
        return backend_mock.get_alerts(station_id)
    params = {"station_id": station_id} if station_id else {}
    return _get("/alerts", params)


# ---------------------------------------------------------------------------
# Public dispatcher — called by gemini_service.py
# ---------------------------------------------------------------------------

_TOOL_MAP = {
    "get_current_stock": _tool_get_current_stock,
    "get_fuel_history": _tool_get_fuel_history,
    "get_alerts": _tool_get_alerts,
}


def execute_tool(name: str, args: dict) -> Any:
    """
    Dispatch a Gemini tool call to the correct implementation.

    Parameters
    ----------
    name : Tool name (must match one of _TOOL_MAP keys).
    args : Arguments dict from Gemini's function_call.

    Returns
    -------
    Any JSON-serializable result.
    """
    fn = _TOOL_MAP.get(name)
    if fn is None:
        raise ValueError(f"Unknown tool: {name!r}. Available: {list(_TOOL_MAP)}")

    logger.debug("Executing tool %s with args %s (mode=%s)", name, args, settings.BACKEND_MODE)
    return fn(**args)
