"""
services/alert_enricher.py
--------------------------
Adds LLM-generated explanation and recommended_action to a list of alerts.

Design decisions
----------------
- Processes alerts concurrently using asyncio.gather so a list of 10 alerts
  doesn't take 10x longer than a single one.
- Gracefully degrades: if Gemini fails for one alert, the rest still work.
- Rate-limiting: limits concurrent Gemini calls to avoid quota errors.
"""

from __future__ import annotations
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from services.gemini_service import explain_alert

logger = logging.getLogger(__name__)

# Max parallel Gemini calls for alert enrichment
_MAX_CONCURRENT = 3
_executor = ThreadPoolExecutor(max_workers=_MAX_CONCURRENT)


async def enrich_alert(alert: dict) -> dict:
    """
    Add 'explanation' and 'recommended_action' fields to a single alert dict.
    Runs the blocking Gemini call in a thread so it doesn't block the event loop.
    """
    loop = asyncio.get_event_loop()
    try:
        explanation, recommended_action = await loop.run_in_executor(
            _executor, explain_alert, alert
        )
    except Exception as exc:
        logger.warning("Failed to enrich alert %s: %s", alert.get("id"), exc)
        explanation = "Unable to generate explanation."
        recommended_action = "Please review this alert manually."

    return {
        **alert,
        "explanation": explanation,
        "recommended_action": recommended_action,
    }


async def enrich_alerts(alerts: list[dict]) -> list[dict]:
    """
    Enrich a list of alerts concurrently.
    Returns the same list with explanation and recommended_action added to each.
    """
    if not alerts:
        return []

    # Use a semaphore to cap concurrency even if asyncio.gather spawns many tasks
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def _bounded_enrich(alert: dict) -> dict:
        async with semaphore:
            return await enrich_alert(alert)

    results = await asyncio.gather(
        *[_bounded_enrich(a) for a in alerts],
        return_exceptions=False,
    )
    return list(results)
