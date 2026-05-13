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
    def __init__(self, events: list[dict[str, Any]] | None = None) -> None:
        self.events = list(events or [])

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)


def test_structured_log_fields_include_lead_event_and_correlation_identifiers() -> None:
    lead_store = SpyLeadStore({"lead_obs_001": {"lead_id": "lead_obs_001"}})
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    response = client.post(
        "/observability/correlation-log",
        json={"lead_id": "lead_obs_001", "event_type": "test.event"},
        headers={"X-Correlation-ID": "corr-abc-123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lead_id"] == "lead_obs_001"
    assert body["event_id"].startswith("evt_")
    assert body["correlation_id"] == "corr-abc-123"

    assert len(publisher.events) == 1
    assert publisher.events[0]["correlation_id"] == "corr-abc-123"

    app.dependency_overrides.clear()


def test_daily_kpis_include_first_response_follow_up_completion_and_tours_per_100() -> None:
    now = datetime.now(timezone.utc)
    created = now - timedelta(hours=6)
    first_touch = created + timedelta(minutes=20)

    lead_store = SpyLeadStore(
        {
            "lead_kpi_001": {"lead_id": "lead_kpi_001", "status": "booked"},
            "lead_kpi_002": {"lead_id": "lead_kpi_002", "status": "assigned"},
        }
    )
    publisher = SpyEventPublisher(
        [
            {
                "event_id": "evt_1",
                "event_type": "lead.created",
                "lead_id": "lead_kpi_001",
                "occurred_at": created.isoformat(),
            },
            {
                "event_id": "evt_2",
                "event_type": "outreach.attempted",
                "lead_id": "lead_kpi_001",
                "occurred_at": first_touch.isoformat(),
            },
            {
                "event_id": "evt_3",
                "event_type": "outreach.continuation_planned",
                "lead_id": "lead_kpi_001",
                "active": True,
                "scheduled_touchpoints": ["T+24h", "T+72h"],
                "occurred_at": now.isoformat(),
            },
            {
                "event_id": "evt_4",
                "event_type": "booking.confirmed",
                "lead_id": "lead_kpi_001",
                "occurred_at": now.isoformat(),
            },
            {
                "event_id": "evt_5",
                "event_type": "lead.created",
                "lead_id": "lead_kpi_002",
                "occurred_at": (now - timedelta(hours=4)).isoformat(),
            },
        ]
    )

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    response = client.get("/observability/kpi/daily")

    assert response.status_code == 200
    body = response.json()
    assert body["lead_count"] == 2
    assert body["first_response_time_minutes"] == 20.0
    assert body["follow_up_completion_rate"] == 0.5
    assert body["tours_per_100_leads"] == 50.0

    app.dependency_overrides.clear()


def test_alerting_covers_webhook_failures_dlq_growth_and_booking_failures() -> None:
    now = datetime.now(timezone.utc).isoformat()
    lead_store = SpyLeadStore({})
    publisher = SpyEventPublisher(
        [
            {"event_id": "evt_a", "event_type": "webhook.failed", "occurred_at": now},
            {"event_id": "evt_b", "event_type": "webhook.failed", "occurred_at": now},
            {"event_id": "evt_c", "event_type": "dlq.growth", "delta": 8, "occurred_at": now},
            {"event_id": "evt_d", "event_type": "booking.failed", "occurred_at": now},
            {"event_id": "evt_e", "event_type": "booking.failed", "occurred_at": now},
            {"event_id": "evt_f", "event_type": "booking.failed", "occurred_at": now},
        ]
    )

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    response = client.get("/observability/alerts/evaluate")

    assert response.status_code == 200
    alerts = response.json()["alerts"]
    names = {a["name"] for a in alerts}
    assert "webhook_failures" in names
    assert "dlq_growth" in names
    assert "booking_failures" in names

    app.dependency_overrides.clear()
