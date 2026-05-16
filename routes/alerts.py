"""
routes/alerts.py
----------------
GET /alerts — Returns alerts enriched with LLM plain-English explanations.

This route mirrors the main project's /alerts endpoint but adds two new fields
per alert: `explanation` and `recommended_action`.

The Angular AlertService  needs NO changes — it just starts
rendering the new fields when they appear in the response.

Query parameters
----------------
station_id  (optional) : Filter alerts to a specific station.
enrich      (optional) : Set to false to skip LLM enrichment (faster, for testing).
                         Default: true.
"""

import logging
from fastapi import APIRouter, Query

from schemas import AlertResponse
from services.alert_enricher import enrich_alerts
from mocks import backend_mock
from config import settings
import httpx

logger = logging.getLogger(__name__)
router = APIRouter()


def _fetch_raw_alerts(station_id: str | None) -> list[dict]:
    """Fetch raw alerts from real backend or mock."""
    if settings.is_mock():
        return backend_mock.get_alerts(station_id)
    params = {"station_id": station_id} if station_id else {}
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{settings.BACKEND_URL}/alerts", params=params)
        resp.raise_for_status()
        return resp.json()


@router.get("/alerts", response_model=list[AlertResponse], tags=["Alerts"])
async def get_alerts(
    station_id: str | None = Query(default=None, description="Filter by station ID"),
    enrich: bool = Query(default=True, description="Set false to skip LLM enrichment"),
) -> list[AlertResponse]:
    """
    Returns all active alerts, each enriched with an LLM-generated explanation
    and recommended action.

    Set ?enrich=false for fast responses without LLM calls (useful during testing).
    """
    raw_alerts = _fetch_raw_alerts(station_id)
    logger.info("Fetched %d raw alerts (enrich=%s)", len(raw_alerts), enrich)

    if enrich and raw_alerts:
        enriched = await enrich_alerts(raw_alerts)
    else:
        # Return alerts as-is with null explanation fields
        enriched = [
            {**a, "explanation": None, "recommended_action": None}
            for a in raw_alerts
        ]

    return [AlertResponse(**a) for a in enriched]
