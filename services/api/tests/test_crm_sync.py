from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_crm_client, get_event_publisher, get_lead_store


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


class StubCRMClient:
    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.upserts: list[dict[str, Any]] = []
        self.tasks: list[dict[str, Any]] = []

    def upsert_lead(self, payload: dict[str, Any]) -> str:
        if self.mode == "outage":
            raise RuntimeError("crm_outage")
        self.upserts.append(payload)
        return "crm_lead_001"

    def create_task(self, payload: dict[str, Any]) -> str:
        if self.mode == "outage":
            raise RuntimeError("crm_outage")
        self.tasks.append(payload)
        return "crm_task_001"



def _lead(lead_id: str) -> dict[str, Any]:
    return {
        "lead_id": lead_id,
        "status": "assigned",
        "owner_agent_id": "agent_001",
        "qualification_state": "fully_qualified",
        "confidence": 0.9,
        "escalation_flags": {
            "missing_fields": False,
            "low_confidence": True,
            "conflict": False,
            "complex_query": False,
            "callback_requested": False,
        },
        "booking_control_mode": "brokerage_controlled",
        "last_activity_at": "2026-05-06T10:00:00+00:00",
        "internal_transcript": "PRIVATE FULL TRANSCRIPT",
    }


def test_crm_sync_mirrors_summary_notes_and_lifecycle_with_canonical_mapping() -> None:
    lead_store = SpyLeadStore(_lead("lead_crm_001"))
    publisher = SpyEventPublisher()
    crm = StubCRMClient(mode="ok")

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_crm_client] = lambda: crm

    client = TestClient(app)
    response = client.post(
        "/leads/lead_crm_001/crm/sync",
        json={"summary_note": "Lead asked for Friday site visit.", "create_escalation_task": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["synced"] is True
    assert body["queued"] is False

    assert len(crm.upserts) == 1
    mirrored = crm.upserts[0]
    assert mirrored["lead_id"] == "lead_crm_001"
    assert mirrored["status"] == "assigned"
    assert mirrored["qualification_state"] == "fully_qualified"
    assert mirrored["summary_note"] == "Lead asked for Friday site visit."
    assert "internal_transcript" not in mirrored

    app.dependency_overrides.clear()


def test_crm_sync_creates_escalation_task_for_brokerage_follow_up() -> None:
    lead_store = SpyLeadStore(_lead("lead_crm_002"))
    publisher = SpyEventPublisher()
    crm = StubCRMClient(mode="ok")

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_crm_client] = lambda: crm

    client = TestClient(app)
    response = client.post(
        "/leads/lead_crm_002/crm/sync",
        json={"summary_note": "Needs human callback.", "create_escalation_task": True},
    )

    assert response.status_code == 200
    assert len(crm.tasks) == 1
    task = crm.tasks[0]
    assert task["lead_id"] == "lead_crm_002"
    assert task["owner_agent_id"] == "agent_001"
    assert task["type"] == "brokerage_follow_up"

    app.dependency_overrides.clear()


def test_crm_outage_queues_retry_and_does_not_break_flow() -> None:
    lead_store = SpyLeadStore(_lead("lead_crm_003"))
    publisher = SpyEventPublisher()
    crm = StubCRMClient(mode="outage")

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_crm_client] = lambda: crm

    client = TestClient(app)
    sync_response = client.post(
        "/leads/lead_crm_003/crm/sync",
        json={"summary_note": "Queue this if CRM is down.", "create_escalation_task": True},
    )
    assert sync_response.status_code == 202
    assert sync_response.json()["synced"] is False
    assert sync_response.json()["queued"] is True

    queue_response = client.get("/crm/sync-queue")
    assert queue_response.status_code == 200
    assert queue_response.json()["queued_count"] >= 1

    retry_response = client.post("/crm/sync-queue/retry")
    assert retry_response.status_code == 200
    assert retry_response.json()["retried"] >= 1

    app.dependency_overrides.clear()
