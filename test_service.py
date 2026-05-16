"""
test_service.py
---------------
Quick integration tests you can run while the service is running.
This is NOT a pytest file — it's a simple script that prints results.

Usage (with service running):
    python test_service.py

All tests use the mock backend so no real backend is needed.
"""

import json
import sys
import httpx

BASE = "http://localhost:8001"


def separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_health() -> bool:
    separator("GET /health")
    resp = httpx.get(f"{BASE}/health")
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
    return resp.status_code == 200


def test_alerts_no_enrich() -> bool:
    separator("GET /alerts?enrich=false (fast, no LLM)")
    resp = httpx.get(f"{BASE}/alerts", params={"enrich": "false"})
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Got {len(data)} alerts")
    for a in data:
        print(f"  [{a['severity'].upper()}] {a['alert_type']} — explanation: {a['explanation']}")
    return resp.status_code == 200


def test_alerts_with_enrich() -> bool:
    separator("GET /alerts?enrich=true (with LLM explanations)")
    print("Note: this calls Gemini — may take a few seconds...")
    resp = httpx.get(f"{BASE}/alerts", params={"enrich": "true"}, timeout=60.0)
    print(f"Status: {resp.status_code}")
    if resp.status_code != 200:
        print("Error:", resp.text)
        return False
    data = resp.json()
    print(f"Got {len(data)} enriched alerts")
    for a in data:
        print(f"\n  Alert #{a['id']} [{a['severity'].upper()}] {a['alert_type']}")
        print(f"  Explanation: {a['explanation']}")
        print(f"  Action: {a['recommended_action']}")
    return True


def test_chat_simple() -> bool:
    separator("POST /chat — simple stock question")
    payload = {
        "message": "What is the current fuel stock at station AGIL-001?",
        "history": [],
        "session_id": "test-session-1",
        "station_id": "AGIL-001",
    }
    print("Sending:", json.dumps(payload, indent=2))
    resp = httpx.post(f"{BASE}/chat", json=payload, timeout=60.0)
    print(f"Status: {resp.status_code}")
    if resp.status_code != 200:
        print("Error:", resp.text)
        return False
    data = resp.json()
    print(f"Response: {data['response']}")
    print(f"Sources used: {data['sources_used']}")
    return True


def test_chat_multi_turn() -> bool:
    separator("POST /chat — multi-turn conversation")
    history = [
        {"role": "user", "content": "What alerts are active right now?"},
        {"role": "assistant", "content": "There is a high-severity low stock alert for Essence at AGIL-001."},
    ]
    payload = {
        "message": "What should I do about that low stock alert?",
        "history": history,
        "session_id": "test-session-2",
    }
    resp = httpx.post(f"{BASE}/chat", json=payload, timeout=60.0)
    print(f"Status: {resp.status_code}")
    if resp.status_code != 200:
        print("Error:", resp.text)
        return False
    data = resp.json()
    print(f"Response: {data['response']}")
    print(f"Sources used: {data['sources_used']}")
    return True


if __name__ == "__main__":
    print(" Microservice — Integration Tests")
    print(f"Target: {BASE}")

    results = []
    results.append(("health", test_health()))
    results.append(("alerts_no_enrich", test_alerts_no_enrich()))

    # LLM tests — skip if user passes --no-llm
    if "--no-llm" not in sys.argv:
        results.append(("alerts_with_enrich", test_alerts_with_enrich()))
        results.append(("chat_simple", test_chat_simple()))
        results.append(("chat_multi_turn", test_chat_multi_turn()))
    else:
        print("\n[--no-llm] Skipping LLM tests.")

    separator("RESULTS")
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    print()
    sys.exit(0 if all_passed else 1)
