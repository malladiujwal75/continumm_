import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import Database
from app.main import app, get_db, get_hindsight_client
from tests.fake_hindsight import FakeHindsight


@pytest.fixture
def client(tmp_path):
    test_db = Database(str(tmp_path / "api_test.db"))
    fake = FakeHindsight()

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_hindsight_client] = lambda: fake
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_seed_then_list_customers(client):
    seed_resp = client.post("/api/demo/seed")
    assert seed_resp.status_code == 200
    body = seed_resp.json()
    assert body["customers_seeded"] == 5
    assert len(body["live_tickets"]) == 3  # marcus, priya, dana have live tickets

    list_resp = client.get("/api/customers")
    assert list_resp.status_code == 200
    names = {c["name"] for c in list_resp.json()}
    assert "Marcus Chen" in names
    assert "Priya Nair" in names


def test_seed_then_send_message_with_memory(client):
    seed_resp = client.post("/api/demo/seed")
    live = seed_resp.json()["live_tickets"]
    marcus_ticket = next(t for t in live if t["customer_id"] == "marcus")

    send_resp = client.post(
        f"/api/tickets/{marcus_ticket['ticket_id']}/messages",
        json={"message": marcus_ticket["suggested_message"], "memory_mode": "on"},
    )
    assert send_resp.status_code == 200
    reply = send_resp.json()
    assert reply["role"] == "agent"
    assert reply["memory_mode"] == "on"
    # Marcus has 3 prior history tickets already seeded -> memory should be non-trivial
    assert reply["meta"]["memories_used"] > 0


def test_send_message_without_memory_uses_baseline(client):
    seed_resp = client.post("/api/demo/seed")
    live = seed_resp.json()["live_tickets"]
    priya_ticket = next(t for t in live if t["customer_id"] == "priya")

    send_resp = client.post(
        f"/api/tickets/{priya_ticket['ticket_id']}/messages",
        json={"message": priya_ticket["suggested_message"], "memory_mode": "off"},
    )
    assert send_resp.status_code == 200
    reply = send_resp.json()
    assert reply["memory_mode"] == "off"
    assert "note" in reply["meta"]


def test_compare_endpoint_returns_both_strategies(client):
    client.post("/api/demo/seed")
    resp = client.post(
        "/api/compare",
        json={"customer_id": "marcus", "message": "my sync is stuck again over VPN"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "with_memory" in body and "without_memory" in body
    assert body["with_memory"]["text"]
    assert body["without_memory"]["text"]


def test_customer_memory_insight_endpoint(client):
    client.post("/api/demo/seed")
    resp = client.get("/api/customers/marcus/memory")
    assert resp.status_code == 200
    body = resp.json()
    assert body["customer_profile"] is not None
    assert body["known_issues_digest"] is not None


def test_send_message_to_unknown_ticket_404s(client):
    resp = client.post(
        "/api/tickets/does-not-exist/messages", json={"message": "hi", "memory_mode": "on"}
    )
    assert resp.status_code == 404
