"""
mocks/backend_mock.py
---------------------
Fake responses that mirror what the real backend (port 8000) returns.

When BACKEND_MODE=mock, agent_tools.py calls functions here instead of
making real HTTP requests.  Replace with real HTTP calls by setting
BACKEND_MODE=real in .env — no other code needs to change.

Keep this file updated whenever the main project changes its response shapes.
"""

from datetime import datetime, timedelta
import random


def get_current(station_id: str | None = None) -> dict:
    """Mirrors GET /current."""
    stations = [
        {
            "station_id": "AGIL-001",
            "station_name": "AGIL Tunis Centre",
            "fuel_type": "Diesel",
            "stock_liters": 4200.0,
            "capacity_liters": 10000.0,
            "price_per_liter": 1.85,
            "timestamp": datetime.utcnow().isoformat(),
        },
        {
            "station_id": "AGIL-001",
            "station_name": "AGIL Tunis Centre",
            "fuel_type": "Essence",
            "stock_liters": 1100.0,
            "capacity_liters": 8000.0,
            "price_per_liter": 1.95,
            "timestamp": datetime.utcnow().isoformat(),
        },
        {
            "station_id": "AGIL-002",
            "station_name": "AGIL Sfax Nord",
            "fuel_type": "Diesel",
            "stock_liters": 9500.0,
            "capacity_liters": 12000.0,
            "price_per_liter": 1.85,
            "timestamp": datetime.utcnow().isoformat(),
        },
    ]
    if station_id:
        return [s for s in stations if s["station_id"] == station_id]
    return stations


def get_history(station_id: str | None = None, limit: int = 20) -> list[dict]:
    """Mirrors GET /history."""
    base_time = datetime.utcnow()
    records = []
    stock = 5000.0
    for i in range(limit):
        stock = max(0, stock - random.uniform(50, 200))
        records.append({
            "station_id": station_id or "AGIL-001",
            "fuel_type": "Diesel",
            "stock_liters": round(stock, 1),
            "price_per_liter": 1.85,
            "sales_liters": round(random.uniform(50, 200), 1),
            "timestamp": (base_time - timedelta(minutes=5 * i)).isoformat(),
        })
    return records


def get_alerts(station_id: str | None = None) -> list[dict]:
    """Mirrors GET /alerts (without LLM explanation — that's added by alert_enricher)."""
    alerts = [
        {
            "id": 1,
            "station_id": "AGIL-001",
            "fuel_type": "Essence",
            "alert_type": "low_stock",
            "severity": "high",
            "message": "Essence stock at AGIL-001 is below 15% capacity (1100 / 8000 L).",
            "timestamp": (datetime.utcnow() - timedelta(minutes=12)).isoformat(),
        },
        {
            "id": 2,
            "station_id": "AGIL-001",
            "fuel_type": "Diesel",
            "alert_type": "high_consumption",
            "severity": "medium",
            "message": "Diesel consumption rate spiked 40% above average in the last hour.",
            "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
        },
        {
            "id": 3,
            "station_id": "AGIL-002",
            "fuel_type": "Diesel",
            "alert_type": "price_anomaly",
            "severity": "low",
            "message": "Diesel price at AGIL-002 deviates 8% from regional average.",
            "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        },
    ]
    if station_id:
        return [a for a in alerts if a["station_id"] == station_id]
    return alerts
