from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_email_sender, get_event_publisher, get_lead_store, get_whatsapp_sender


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


class StubWhatsAppSender:
    def __init__(self) -> None:
        self.calls = 0

    def send_first_touch(self, lead_id: str, phone: str, first_name: str) -> str:
        self.calls += 1
        return "delivered"


class StubEmailSender:
    def __init__(self) -> None:
        self.calls = 0

    def send_first_touch(self, lead_id: str, email: str, first_name: str) -> str:
        self.calls += 1
        return "sent"


def _base_lead(lead_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
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
        "last_activity_at": now,
    }


def test_pause_and_resume_automation_controls() -> None:
    lead_store = SpyLeadStore(_base_lead("lead_human_001"))
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    pause = client.post("/leads/lead_human_001/automation/pause")
    assert pause.status_code == 200
    assert pause.json()["automation_paused"] is True

    paused = client.get("/leads/lead_human_001")
    assert paused.status_code == 200
    assert paused.json()["automation_paused"] is True

    resume = client.post("/leads/lead_human_001/automation/resume")
    assert resume.status_code == 200
    assert resume.json()["automation_paused"] is False

    resumed = client.get("/leads/lead_human_001")
    assert resumed.json()["automation_paused"] is False
    assert len(publisher.events) == 2
    assert publisher.events[0]["event_type"] == "lead.automation_paused"
    assert publisher.events[1]["event_type"] == "lead.automation_resumed"

    app.dependency_overrides.clear()


def test_manual_takeover_sets_brokerage_controlled_and_assist_mode_checkpoint() -> None:
    lead_store = SpyLeadStore(_base_lead("lead_human_002"))
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    response = client.post(
        "/leads/lead_human_002/takeover",
        json={"actor_user_id": "broker_007", "actor_role": "brokerage_agent"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["booking_control_mode"] == "brokerage_controlled"
    assert body["assist_mode"] == "draft_only"
    checkpoint_at = datetime.fromisoformat(body["checkpoint_at"])
    created_at = datetime.fromisoformat(body["takeover_at"])
    assert checkpoint_at - created_at >= timedelta(hours=71, minutes=59)

    stored = client.get("/leads/lead_human_002").json()
    assert stored["booking_control_mode"] == "brokerage_controlled"

    assert len(publisher.events) == 1
    assert publisher.events[0]["event_type"] == "lead.manual_takeover_enabled"

    app.dependency_overrides.clear()


def test_single_cadence_continuity_toggle_not_per_message() -> None:
    lead_store = SpyLeadStore(_base_lead("lead_human_003"))
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    on = client.post(
        "/leads/lead_human_003/cadence-continuity",
        json={"continuity_approved": True, "actor_user_id": "admin_001", "actor_role": "admin"},
    )
    assert on.status_code == 200
    assert on.json()["continuity_approved"] is True

    off = client.post(
        "/leads/lead_human_003/cadence-continuity",
        json={"continuity_approved": False, "actor_user_id": "admin_001", "actor_role": "admin"},
    )
    assert off.status_code == 200
    assert off.json()["continuity_approved"] is False

    events = publisher.events
    assert len(events) == 2
    assert events[0]["event_type"] == "lead.cadence_continuity_changed"
    assert events[0]["continuity_approved"] is True
    assert events[1]["event_type"] == "lead.cadence_continuity_changed"
    assert events[1]["continuity_approved"] is False

    app.dependency_overrides.clear()


def test_pause_blocks_autonomous_outreach_but_manual_controls_still_allowed() -> None:
    lead = _base_lead("lead_human_004")
    lead["automation_paused"] = True

    lead_store = SpyLeadStore(lead)
    publisher = SpyEventPublisher()
    whatsapp = StubWhatsAppSender()
    email = StubEmailSender()

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_whatsapp_sender] = lambda: whatsapp
    app.dependency_overrides[get_email_sender] = lambda: email

    client = TestClient(app)

    blocked = client.post(
        "/outreach/first-touch",
        json={
            "lead_id": "lead_human_004",
            "phone": "+919777777777",
            "email": "human4@example.com",
            "first_name": "Dia",
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "automation_paused"
    assert whatsapp.calls == 0
    assert email.calls == 0

    manual = client.post("/leads/lead_human_004/automation/resume")
    assert manual.status_code == 200
    assert manual.json()["automation_paused"] is False

    app.dependency_overrides.clear()
