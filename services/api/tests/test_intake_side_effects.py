from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_event_publisher, get_lead_store


class SpyLeadStore:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def create(self, record: dict[str, Any]) -> None:
        self.records.append(record)


class SpyEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)


def test_unique_intake_creates_lead_and_publishes_event_once() -> None:
    lead_store = SpyLeadStore()
    event_publisher = SpyEventPublisher()

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: event_publisher

    client = TestClient(app)

    payload = {
        "source_event_id": "evt_web_side_001",
        "contact": {
            "phone": "+916666666666",
            "email": "side@example.com",
            "first_name": "Mira"
        },
        "preferences": {
            "preferred_locality": "Goregaon",
            "budget_range": "90L-1.2Cr",
            "move_in_timeline": "30_days"
        }
    }

    first = client.post("/intake/website", json=payload)
    second = client.post("/intake/website", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202

    assert len(lead_store.records) == 1
    assert len(event_publisher.events) == 1

    lead = lead_store.records[0]
    assert lead["status"] == "new"
    assert lead["qualification_state"] == "unqualified"
    assert lead["booking_control_mode"] == "autonomous"
    assert lead["automation_paused"] is False

    event = event_publisher.events[0]
    assert event["event_type"] == "lead.created"
    assert event["lead_id"] == lead["lead_id"]

    app.dependency_overrides.clear()
