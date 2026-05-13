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
    def __init__(self, outcomes: list[str]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def create_tour_event(self, lead_id: str, slot: str) -> tuple[str, str | None]:
        self.calls += 1
        if not self.outcomes:
            return ("error", None)
        outcome = self.outcomes.pop(0)
        if outcome == "success":
            return ("success", f"gcal_evt_{lead_id}")
        return (outcome, None)


def _eligible_lead(lead_id: str) -> dict[str, Any]:
    return {
        "lead_id": lead_id,
        "status": "assigned",
        "qualification_state": "fully_qualified",
        "confidence": 0.91,
        "escalation_flags": {
            "missing_fields": False,
            "low_confidence": False,
            "conflict": False,
            "complex_query": False,
            "callback_requested": False,
        },
        "booking_control_mode": "autonomous",
        "automation_paused": False,
    }


def test_booking_gate_blocks_when_not_fully_qualified_or_low_confidence_or_escalated() -> None:
    base = _eligible_lead("lead_book_001")

    for variant in [
        {**base, "qualification_state": "partially_qualified"},
        {**base, "confidence": 0.79},
        {**base, "escalation_flags": {**base["escalation_flags"], "low_confidence": True}},
    ]:
        lead_store = SpyLeadStore(variant)
        publisher = SpyEventPublisher()
        calendar = StubCalendarWriter(["success"])
        app.dependency_overrides[get_lead_store] = lambda: lead_store
        app.dependency_overrides[get_event_publisher] = lambda: publisher
        app.dependency_overrides[get_calendar_writer] = lambda: calendar

        client = TestClient(app)
        response = client.post(
            "/leads/lead_book_001/booking/attempt",
            json={"slot": "2026-05-20T11:00:00+05:30", "fallback_slots": []},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "autonomous_booking_gate_failed"
        assert calendar.calls == 0
        app.dependency_overrides.clear()


def test_booking_confirms_only_after_calendar_write_success() -> None:
    lead_store = SpyLeadStore(_eligible_lead("lead_book_002"))
    publisher = SpyEventPublisher()
    calendar = StubCalendarWriter(["success"])
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_calendar_writer] = lambda: calendar

    client = TestClient(app)
    response = client.post(
        "/leads/lead_book_002/booking/attempt",
        json={"slot": "2026-05-21T10:00:00+05:30", "fallback_slots": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["confirmed"] is True
    assert body["calendar_event_id"] == "gcal_evt_lead_book_002"

    lead = client.get("/leads/lead_book_002").json()
    assert lead["status"] == "booked"
    assert lead["booking_status"] == "confirmed"

    event_types = [e["event_type"] for e in publisher.events]
    assert "booking.in_progress" in event_types
    assert "booking.confirmed" in event_types

    app.dependency_overrides.clear()


def test_booking_failure_retries_and_returns_alternatives() -> None:
    lead_store = SpyLeadStore(_eligible_lead("lead_book_003"))
    publisher = SpyEventPublisher()
    calendar = StubCalendarWriter(["conflict", "error"])
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_calendar_writer] = lambda: calendar

    client = TestClient(app)
    response = client.post(
        "/leads/lead_book_003/booking/attempt",
        json={
            "slot": "2026-05-22T09:00:00+05:30",
            "fallback_slots": [
                "2026-05-22T10:00:00+05:30",
                "2026-05-22T11:00:00+05:30",
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "retry_required"
    assert body["confirmed"] is False
    assert body["calendar_event_id"] is None
    assert body["recommended_slots"] == [
        "2026-05-22T10:00:00+05:30",
        "2026-05-22T11:00:00+05:30",
    ]
    assert calendar.calls == 2

    lead = client.get("/leads/lead_book_003").json()
    assert lead["status"] == "assigned"
    assert lead["booking_status"] == "retry_required"

    event_types = [e["event_type"] for e in publisher.events]
    assert "booking.in_progress" in event_types
    assert "booking.failed" in event_types

    app.dependency_overrides.clear()
