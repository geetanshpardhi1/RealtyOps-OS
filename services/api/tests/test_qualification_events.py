from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_event_publisher, get_lead_store


class SpyLeadStore:
    def create(self, record: dict[str, Any]) -> None:
        return None

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        return None

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        return None


class SpyEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)


def test_qualification_emits_lead_qualified_event() -> None:
    lead_store = SpyLeadStore()
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    payload = {
        "lead_id": "lead_q_event_001",
        "contact": {
            "phone": "+919444444444",
            "email": "qevent@example.com",
            "phone_verified": True,
            "email_verified": True,
        },
        "preferences": {
            "preferred_locality": "Powai",
            "budget_range": "80L-1Cr",
            "move_in_timeline": "30_days",
        },
    }

    response = client.post("/qualification/evaluate", json=payload)

    assert response.status_code == 200
    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event["event_type"] == "lead.qualified"
    assert event["lead_id"] == "lead_q_event_001"
    assert event["qualification_state"] == "fully_qualified"
    assert event["assignment_gate_passed"] is True

    app.dependency_overrides.clear()
