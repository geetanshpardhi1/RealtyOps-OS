from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_event_publisher, get_lead_store


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


def _lead(lead_id: str, *, status: str = "assigned", qstate: str = "fully_qualified") -> dict[str, Any]:
    return {
        "lead_id": lead_id,
        "status": status,
        "qualification_state": qstate,
        "owner_agent_id": "agent_001",
        "automation_paused": False,
        "last_activity_at": datetime.now(timezone.utc).isoformat(),
        "contact": {"phone": "+919111111111", "email": "a@example.com"},
    }


def test_auto_close_after_inactivity_and_preserve_qualification_state() -> None:
    stale = _lead("lead_life_001", status="assigned", qstate="partially_qualified")
    stale["last_activity_at"] = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()

    store = SpyLeadStore({"lead_life_001": stale})
    events = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: events

    client = TestClient(app)
    response = client.post("/lifecycle/auto-close/run", json={"inactivity_days": 14})

    assert response.status_code == 200
    assert response.json()["closed_count"] == 1

    lead = client.get("/leads/lead_life_001").json()
    assert lead["status"] == "closed"
    assert lead["qualification_state"] == "partially_qualified"

    app.dependency_overrides.clear()


def test_inbound_auto_reopen_preserves_owner() -> None:
    closed = _lead("lead_life_002", status="closed", qstate="fully_qualified")
    closed["owner_agent_id"] = "agent_002"

    store = SpyLeadStore({"lead_life_002": closed})
    events = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: events

    client = TestClient(app)
    response = client.post("/leads/lead_life_002/lifecycle/inbound-reopen")

    assert response.status_code == 200
    assert response.json()["reopened"] is True

    lead = client.get("/leads/lead_life_002").json()
    assert lead["status"] == "assigned"
    assert lead["owner_agent_id"] == "agent_002"

    app.dependency_overrides.clear()


def test_identity_merge_exact_phone_auto_merge() -> None:
    primary = _lead("lead_life_003")
    primary["contact"] = {"phone": "+919123456789", "email": "x@example.com"}
    incoming = {"phone": "+919123456789", "email": "different@example.com"}

    store = SpyLeadStore({"lead_life_003": primary})
    events = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: events

    client = TestClient(app)
    response = client.post("/lifecycle/identity-merge/evaluate", json={"lead_id": "lead_life_003", "incoming": incoming})

    assert response.status_code == 200
    assert response.json()["decision"] == "auto_merge"
    assert response.json()["reason"] == "exact_phone_match"

    app.dependency_overrides.clear()


def test_identity_merge_email_only_when_phone_missing() -> None:
    primary = _lead("lead_life_004")
    primary["contact"] = {"phone": "", "email": "same@example.com"}
    incoming = {"phone": "", "email": "same@example.com"}

    store = SpyLeadStore({"lead_life_004": primary})
    events = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: events

    client = TestClient(app)
    response = client.post("/lifecycle/identity-merge/evaluate", json={"lead_id": "lead_life_004", "incoming": incoming})

    assert response.status_code == 200
    assert response.json()["decision"] == "auto_merge"
    assert response.json()["reason"] == "exact_email_match_phone_missing"

    app.dependency_overrides.clear()


def test_identity_conflict_flags_human_review_not_blind_merge() -> None:
    primary = _lead("lead_life_005")
    primary["contact"] = {"phone": "+919111111111", "email": "old@example.com"}
    incoming = {"phone": "+919222222222", "email": "new@example.com"}

    store = SpyLeadStore({"lead_life_005": primary})
    events = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: events

    client = TestClient(app)
    response = client.post("/lifecycle/identity-merge/evaluate", json={"lead_id": "lead_life_005", "incoming": incoming})

    assert response.status_code == 200
    assert response.json()["decision"] == "human_review"
    assert response.json()["reason"] == "identity_conflict"

    lead = client.get("/leads/lead_life_005").json()
    flags = lead.get("escalation_flags", {})
    assert flags.get("conflict") is True

    app.dependency_overrides.clear()
