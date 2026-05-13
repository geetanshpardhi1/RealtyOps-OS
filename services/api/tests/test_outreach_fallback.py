from typing import Any

from fastapi.testclient import TestClient

from app.main import (
    app,
    get_email_sender,
    get_event_publisher,
    get_lead_store,
    get_whatsapp_sender,
)


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
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.calls = 0

    def send_first_touch(self, lead_id: str, phone: str, first_name: str) -> str:
        self.calls += 1
        return self.outcome


class StubEmailSender:
    def __init__(self) -> None:
        self.calls = 0

    def send_first_touch(self, lead_id: str, email: str, first_name: str) -> str:
        self.calls += 1
        return "sent"


def test_outreach_uses_whatsapp_first_without_email_fallback_on_delivery() -> None:
    lead_store = SpyLeadStore(
        {"lead_id": "lead_outreach_001", "qualification_state": "fully_qualified"}
    )
    publisher = SpyEventPublisher()
    whatsapp = StubWhatsAppSender("delivered")
    email = StubEmailSender()

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_whatsapp_sender] = lambda: whatsapp
    app.dependency_overrides[get_email_sender] = lambda: email

    client = TestClient(app)
    response = client.post(
        "/outreach/first-touch",
        json={
            "lead_id": "lead_outreach_001",
            "phone": "+919111111111",
            "email": "lead1@example.com",
            "first_name": "Ari",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["primary_channel"] == "whatsapp"
    assert body["whatsapp_outcome"] == "delivered"
    assert body["email_fallback_triggered"] is False
    assert whatsapp.calls == 1
    assert email.calls == 0
    assert len(publisher.events) == 1
    assert publisher.events[0]["channel"] == "whatsapp"
    assert publisher.events[0]["delivery_outcome"] == "delivered"

    app.dependency_overrides.clear()


def test_outreach_falls_back_to_email_only_on_whatsapp_failure() -> None:
    lead_store = SpyLeadStore(
        {"lead_id": "lead_outreach_002", "qualification_state": "partially_qualified"}
    )
    publisher = SpyEventPublisher()
    whatsapp = StubWhatsAppSender("undelivered")
    email = StubEmailSender()

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_whatsapp_sender] = lambda: whatsapp
    app.dependency_overrides[get_email_sender] = lambda: email

    client = TestClient(app)
    response = client.post(
        "/outreach/first-touch",
        json={
            "lead_id": "lead_outreach_002",
            "phone": "+919222222222",
            "email": "lead2@example.com",
            "first_name": "Bea",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["whatsapp_outcome"] == "undelivered"
    assert body["email_fallback_triggered"] is True
    assert body["email_outcome"] == "sent"
    assert whatsapp.calls == 1
    assert email.calls == 1
    assert len(publisher.events) == 2
    assert publisher.events[0]["channel"] == "whatsapp"
    assert publisher.events[0]["delivery_outcome"] == "undelivered"
    assert publisher.events[1]["channel"] == "email"
    assert publisher.events[1]["delivery_outcome"] == "sent"

    app.dependency_overrides.clear()


def test_outreach_rejects_unqualified_lead_as_not_eligible() -> None:
    lead_store = SpyLeadStore({"lead_id": "lead_outreach_003", "qualification_state": "unqualified"})
    publisher = SpyEventPublisher()
    whatsapp = StubWhatsAppSender("delivered")
    email = StubEmailSender()

    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    app.dependency_overrides[get_whatsapp_sender] = lambda: whatsapp
    app.dependency_overrides[get_email_sender] = lambda: email

    client = TestClient(app)
    response = client.post(
        "/outreach/first-touch",
        json={
            "lead_id": "lead_outreach_003",
            "phone": "+919333333333",
            "email": "lead3@example.com",
            "first_name": "Cia",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "lead_not_eligible_for_outreach"
    assert whatsapp.calls == 0
    assert email.calls == 0
    assert len(publisher.events) == 0

    app.dependency_overrides.clear()
