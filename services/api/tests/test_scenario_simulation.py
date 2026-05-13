from typing import Any

from fastapi.testclient import TestClient

from app.main import (
    app,
    get_calendar_writer,
    get_crm_client,
    get_email_sender,
    get_event_publisher,
    get_lead_store,
    get_whatsapp_sender,
)


class SpyLeadStore:
    def __init__(self, records: dict[str, dict[str, Any]]) -> None:
        self.records = {k: dict(v) for k, v in records.items()}

    def create(self, record: dict[str, Any]) -> None:
        self.records[str(record["lead_id"])] = dict(record)

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        if lead_id not in self.records:
            self.records[lead_id] = {"lead_id": lead_id}
        self.records[lead_id].update(fields)

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        rec = self.records.get(lead_id)
        return dict(rec) if rec else None


class SpyEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)


class StubWhatsAppSender:
    def send_first_touch(self, lead_id: str, phone: str, first_name: str) -> str:
        return "undelivered"


class StubEmailSender:
    def send_first_touch(self, lead_id: str, email: str, first_name: str) -> str:
        return "sent"


class StubCalendarWriter:
    def __init__(self, outcomes: list[str]) -> None:
        self.outcomes = list(outcomes)

    def create_tour_event(self, lead_id: str, slot: str) -> tuple[str, str | None]:
        outcome = self.outcomes.pop(0)
        if outcome == "success":
            return ("success", f"gcal_evt_{lead_id}")
        return (outcome, None)


class StubCRMClient:
    def __init__(self, outage_first: bool = True) -> None:
        self.outage_first = outage_first
        self.calls = 0

    def upsert_lead(self, payload: dict[str, Any]) -> str:
        self.calls += 1
        if self.outage_first and self.calls == 1:
            raise RuntimeError("crm_outage")
        return f"crm_{payload['lead_id']}"

    def create_task(self, payload: dict[str, Any]) -> str:
        return f"crm_task_{payload['lead_id']}"


def _lead(lead_id: str) -> dict[str, Any]:
    return {
        "lead_id": lead_id,
        "status": "assigned",
        "owner_agent_id": "agent_001",
        "qualification_state": "fully_qualified",
        "confidence": 0.92,
        "escalation_flags": {
            "missing_fields": False,
            "low_confidence": False,
            "conflict": False,
            "complex_query": False,
            "callback_requested": False,
        },
        "booking_control_mode": "autonomous",
        "automation_paused": False,
        "last_activity_at": "2026-05-06T10:00:00+00:00",
        "contact": {"phone": "+919111111111", "email": "scenario@example.com"},
    }


def test_scenario_whatsapp_failure_email_fallback_then_booking_retry_required() -> None:
    lead = _lead("lead_scn_001")
    store = SpyLeadStore({"lead_scn_001": lead})
    events = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: events
    app.dependency_overrides[get_whatsapp_sender] = lambda: StubWhatsAppSender()
    app.dependency_overrides[get_email_sender] = lambda: StubEmailSender()
    app.dependency_overrides[get_calendar_writer] = lambda: StubCalendarWriter(["conflict", "error"])

    client = TestClient(app)

    outreach = client.post(
        "/outreach/first-touch",
        json={
            "lead_id": "lead_scn_001",
            "phone": "+919111111111",
            "email": "scenario@example.com",
            "first_name": "Geo",
        },
    )
    assert outreach.status_code == 200
    assert outreach.json()["email_fallback_triggered"] is True

    booking = client.post(
        "/leads/lead_scn_001/booking/attempt",
        json={
            "slot": "2026-06-01T10:00:00+05:30",
            "fallback_slots": ["2026-06-01T11:00:00+05:30"],
        },
    )
    assert booking.status_code == 200
    assert booking.json()["status"] == "retry_required"

    event_types = [e["event_type"] for e in events.events]
    assert "outreach.attempted" in event_types
    assert "booking.failed" in event_types

    app.dependency_overrides.clear()


def test_scenario_crm_outage_then_retry_recovers_without_blocking() -> None:
    lead = _lead("lead_scn_002")
    store = SpyLeadStore({"lead_scn_002": lead})
    events = SpyEventPublisher()
    crm = StubCRMClient(outage_first=True)
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: events
    app.dependency_overrides[get_crm_client] = lambda: crm

    client = TestClient(app)

    first_sync = client.post(
        "/leads/lead_scn_002/crm/sync",
        json={"summary_note": "Initial queue due to outage", "create_escalation_task": True},
    )
    assert first_sync.status_code == 202
    assert first_sync.json()["queued"] is True

    queue = client.get("/crm/sync-queue")
    assert queue.status_code == 200
    assert queue.json()["queued_count"] >= 1

    retry = client.post("/crm/sync-queue/retry")
    assert retry.status_code == 200
    assert retry.json()["retried"] >= 1

    queue_after = client.get("/crm/sync-queue")
    assert queue_after.status_code == 200
    assert queue_after.json()["queued_count"] == 0

    event_types = [e["event_type"] for e in events.events]
    assert "crm.sync_queued" in event_types
    assert "crm.sync_retry_executed" in event_types

    app.dependency_overrides.clear()
