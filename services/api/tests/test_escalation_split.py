from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_calendar_writer, get_event_publisher, get_lead_store


class SpyLeadStore:
    def __init__(self, lead: dict[str, Any]) -> None:
        self._lead = dict(lead)

    def create(self, record: dict[str, Any]) -> None:
        return None

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        if lead_id == self._lead["lead_id"]:
            self._lead.update(fields)

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        if lead_id == self._lead["lead_id"]:
            return dict(self._lead)
        return None


class SpyEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)


class StubCalendarWriter:
    def __init__(self) -> None:
        self.calls = 0

    def create_tour_event(self, lead_id: str, slot: str) -> tuple[str, str | None]:
        self.calls += 1
        return ("success", f"gcal_evt_{lead_id}")


def _lead(lead_id: str) -> dict[str, Any]:
    return {
        "lead_id": lead_id,
        "status": "assigned",
        "qualification_state": "fully_qualified",
        "confidence": 0.86,
        "escalation_flags": {
            "missing_fields": False,
            "low_confidence": False,
            "conflict": False,
            "complex_query": False,
            "callback_requested": False,
        },
        "booking_control_mode": "autonomous",
        "automation_paused": False,
        "last_activity_at": datetime.now(timezone.utc).isoformat(),
    }


def test_booking_escalation_triggers_for_low_or_borderline_confidence_and_risk_flags() -> None:
    lead = _lead("lead_escalate_001")
    lead["confidence"] = 0.64
    lead_store = SpyLeadStore(lead)
    publisher = SpyEventPublisher()

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    response = client.post("/leads/lead_escalate_001/escalation/evaluate")

    assert response.status_code == 200
    body = response.json()
    assert body["booking_escalated"] is True
    assert body["booking_control_mode"] == "brokerage_controlled"
    assert "low_confidence" in body["reasons"]

    stored = client.get("/leads/lead_escalate_001").json()
    assert stored["booking_control_mode"] == "brokerage_controlled"
    assert stored["booking_escalated"] is True

    app.dependency_overrides.clear()


def test_outreach_continuation_schedules_t24_and_t72_unless_paused() -> None:
    lead = _lead("lead_escalate_002")
    lead["booking_escalated"] = True
    lead["last_activity_at"] = (datetime.now(timezone.utc) - timedelta(hours=80)).isoformat()

    lead_store = SpyLeadStore(lead)
    publisher = SpyEventPublisher()

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    response = client.post("/leads/lead_escalate_002/outreach/continuation/plan")

    assert response.status_code == 200
    body = response.json()
    assert body["active"] is True
    assert body["scheduled_touchpoints"] == ["T+24h", "T+72h"]

    paused = dict(lead)
    paused["automation_paused"] = True
    app.dependency_overrides[get_lead_store] = lambda: SpyLeadStore(paused)
    paused_response = client.post("/leads/lead_escalate_002/outreach/continuation/plan")
    assert paused_response.status_code == 200
    assert paused_response.json()["active"] is False
    assert paused_response.json()["scheduled_touchpoints"] == []

    app.dependency_overrides.clear()


def test_autonomous_booking_blocked_while_escalation_active() -> None:
    lead = _lead("lead_escalate_003")
    lead["booking_escalated"] = True
    lead["booking_control_mode"] = "brokerage_controlled"
    lead_store = SpyLeadStore(lead)
    publisher = SpyEventPublisher()
    calendar = StubCalendarWriter()

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_calendar_writer] = lambda: calendar

    client = TestClient(app)
    response = client.post(
        "/leads/lead_escalate_003/booking/attempt",
        json={"slot": "2026-05-30T11:00:00+05:30", "fallback_slots": []},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "booking_escalated_human_control_required"
    assert calendar.calls == 0

    app.dependency_overrides.clear()
