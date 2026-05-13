from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_event_publisher, get_lead_store


class SpyLeadStore:
    def __init__(self, records: dict[str, dict[str, Any]], events: list[dict[str, Any]] | None = None) -> None:
        self.records = {k: dict(v) for k, v in records.items()}
        self.events = list(events or [])

    def create(self, record: dict[str, Any]) -> None:
        self.records[str(record["lead_id"])] = dict(record)

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        if lead_id not in self.records:
            self.records[lead_id] = {"lead_id": lead_id}
        self.records[lead_id].update(fields)

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        rec = self.records.get(lead_id)
        return dict(rec) if rec else None

    def list_leads(self) -> list[dict[str, Any]]:
        return [dict(rec) for rec in self.records.values()]

    def append_event(self, event: dict[str, Any]) -> None:
        self.events.append(dict(event))

    def list_events(self, lead_id: str, limit: int = 100) -> list[dict[str, Any]]:
        filtered = [dict(e) for e in self.events if not lead_id or str(e.get("lead_id", "")) == lead_id]
        filtered.sort(key=lambda e: str(e.get("occurred_at", "")), reverse=True)
        return filtered[:limit]


class SpyEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(dict(event))


def test_lead_inbox_lists_leads_with_filters_and_ordering() -> None:
    store = SpyLeadStore(
        records={
            "lead_a": {
                "lead_id": "lead_a",
                "status": "assigned",
                "qualification_state": "fully_qualified",
                "owner_agent_id": "agent_001",
                "updated_at": "2026-05-13T10:10:00+00:00",
            },
            "lead_b": {
                "lead_id": "lead_b",
                "status": "new",
                "qualification_state": "unqualified",
                "owner_agent_id": None,
                "updated_at": "2026-05-13T09:00:00+00:00",
            },
            "lead_c": {
                "lead_id": "lead_c",
                "status": "assigned",
                "qualification_state": "partially_qualified",
                "owner_agent_id": "agent_002",
                "updated_at": "2026-05-13T11:00:00+00:00",
            },
        }
    )
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)

    all_leads = client.get("/leads")
    assert all_leads.status_code == 200
    body = all_leads.json()
    assert body["count"] == 3
    assert [item["lead_id"] for item in body["items"]] == ["lead_c", "lead_a", "lead_b"]

    filtered = client.get(
        "/leads",
        params={"status": "assigned", "qualification_state": "fully_qualified", "owner_agent_id": "agent_001"},
    )
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["count"] == 1
    assert payload["items"][0]["lead_id"] == "lead_a"

    app.dependency_overrides.clear()


def test_lead_timeline_returns_events_for_selected_lead_in_desc_order() -> None:
    store = SpyLeadStore(
        records={
            "lead_tl_001": {
                "lead_id": "lead_tl_001",
                "status": "assigned",
                "qualification_state": "partially_qualified",
                "owner_agent_id": "agent_001",
            },
            "lead_tl_002": {
                "lead_id": "lead_tl_002",
                "status": "assigned",
                "qualification_state": "partially_qualified",
                "owner_agent_id": "agent_002",
            },
        },
        events=[
            {
                "event_id": "evt_001",
                "event_type": "lead.created",
                "lead_id": "lead_tl_001",
                "occurred_at": "2026-05-13T09:00:00+00:00",
            },
            {
                "event_id": "evt_002",
                "event_type": "lead.qualified",
                "lead_id": "lead_tl_001",
                "occurred_at": "2026-05-13T10:00:00+00:00",
            },
            {
                "event_id": "evt_003",
                "event_type": "lead.created",
                "lead_id": "lead_tl_002",
                "occurred_at": "2026-05-13T11:00:00+00:00",
            },
        ],
    )
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    timeline = client.get("/leads/lead_tl_001/timeline")
    assert timeline.status_code == 200
    body = timeline.json()
    assert body["lead_id"] == "lead_tl_001"
    assert body["count"] == 2
    assert [event["event_id"] for event in body["items"]] == ["evt_002", "evt_001"]
    assert all(event["lead_id"] == "lead_tl_001" for event in body["items"])

    app.dependency_overrides.clear()
