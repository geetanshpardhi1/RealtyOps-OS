from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_event_publisher, get_lead_store


class SpyLeadStore:
    def __init__(self, leads: list[dict[str, Any]]) -> None:
        self._records = {lead["lead_id"]: dict(lead) for lead in leads}

    def create(self, record: dict[str, Any]) -> None:
        self._records[str(record["lead_id"])] = dict(record)

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        if lead_id not in self._records:
            self._records[lead_id] = {"lead_id": lead_id}
        self._records[lead_id].update(fields)

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        record = self._records.get(lead_id)
        return dict(record) if record else None


class SpyEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)


def _lead(lead_id: str) -> dict[str, Any]:
    return {
        "lead_id": lead_id,
        "qualification_state": "fully_qualified",
        "automation_paused": False,
    }


def test_slot_proposals_enforce_three_per_cycle_and_max_two_cycles() -> None:
    lead_store = SpyLeadStore([_lead("lead_slot_001")])
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)

    cycle1 = client.post(
        "/leads/lead_slot_001/slot-negotiation/propose",
        json={
            "cycle": 1,
            "candidate_slots": [
                "2026-05-10T10:00:00+05:30",
                "2026-05-10T11:00:00+05:30",
                "2026-05-10T12:00:00+05:30",
            ],
        },
    )
    assert cycle1.status_code == 200
    assert len(cycle1.json()["proposed_slots"]) == 3
    assert cycle1.json()["cycle"] == 1

    too_many = client.post(
        "/leads/lead_slot_001/slot-negotiation/propose",
        json={
            "cycle": 1,
            "candidate_slots": [
                "2026-05-11T10:00:00+05:30",
                "2026-05-11T11:00:00+05:30",
                "2026-05-11T12:00:00+05:30",
                "2026-05-11T13:00:00+05:30",
            ],
        },
    )
    assert too_many.status_code == 422

    cycle3 = client.post(
        "/leads/lead_slot_001/slot-negotiation/propose",
        json={
            "cycle": 3,
            "candidate_slots": [
                "2026-05-12T10:00:00+05:30",
                "2026-05-12T11:00:00+05:30",
                "2026-05-12T12:00:00+05:30",
            ],
        },
    )
    assert cycle3.status_code == 409
    assert cycle3.json()["detail"] == "max_cycles_exceeded"

    app.dependency_overrides.clear()


def test_concurrent_collision_first_confirmed_wins() -> None:
    lead_store = SpyLeadStore([_lead("lead_slot_002a"), _lead("lead_slot_002b")])
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    slot = "2026-05-13T15:00:00+05:30"

    winner = client.post(
        "/leads/lead_slot_002a/slot-negotiation/confirm",
        json={
            "slot": slot,
            "cycle": 1,
            "candidate_slots": [
                slot,
                "2026-05-13T16:00:00+05:30",
                "2026-05-13T17:00:00+05:30",
            ],
        },
    )
    assert winner.status_code == 200
    assert winner.json()["status"] == "confirmed"
    assert winner.json()["confirmed_slot"] == slot

    loser = client.post(
        "/leads/lead_slot_002b/slot-negotiation/confirm",
        json={
            "slot": slot,
            "cycle": 1,
            "candidate_slots": [
                slot,
                "2026-05-13T16:00:00+05:30",
                "2026-05-13T17:00:00+05:30",
            ],
        },
    )
    assert loser.status_code == 200
    assert loser.json()["status"] == "collision"
    assert loser.json()["winner_lead_id"] == "lead_slot_002a"

    app.dependency_overrides.clear()


def test_collision_path_returns_immediate_alternatives() -> None:
    lead_store = SpyLeadStore([_lead("lead_slot_003a"), _lead("lead_slot_003b")])
    publisher = SpyEventPublisher()
    app.dependency_overrides[get_lead_store] = lambda: lead_store
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    client = TestClient(app)
    common_slot = "2026-05-14T10:00:00+05:30"

    _ = client.post(
        "/leads/lead_slot_003a/slot-negotiation/confirm",
        json={
            "slot": common_slot,
            "cycle": 1,
            "candidate_slots": [
                common_slot,
                "2026-05-14T11:00:00+05:30",
                "2026-05-14T12:00:00+05:30",
            ],
        },
    )

    collision = client.post(
        "/leads/lead_slot_003b/slot-negotiation/confirm",
        json={
            "slot": common_slot,
            "cycle": 1,
            "candidate_slots": [
                common_slot,
                "2026-05-14T11:00:00+05:30",
                "2026-05-14T12:00:00+05:30",
            ],
        },
    )
    assert collision.status_code == 200
    body = collision.json()
    assert body["status"] == "collision"
    assert len(body["alternative_slots"]) >= 1
    assert common_slot not in body["alternative_slots"]

    app.dependency_overrides.clear()
