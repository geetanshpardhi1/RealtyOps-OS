from typing import Any

from fastapi.testclient import TestClient

from app.main import app, get_lead_store


class SpyLeadStore:
    def __init__(self) -> None:
        self.updates: list[tuple[str, dict[str, Any]]] = []

    def create(self, record: dict[str, Any]) -> None:
        return None

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        self.updates.append((lead_id, fields))

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        return None


def test_qualification_persists_state_and_assignment() -> None:
    spy = SpyLeadStore()
    app.dependency_overrides[get_lead_store] = lambda: spy

    client = TestClient(app)
    payload = {
        "lead_id": "lead_q_persist_001",
        "contact": {
            "phone": "+919333333333",
            "email": "persist@example.com",
            "phone_verified": True,
            "email_verified": True,
        },
        "preferences": {
            "preferred_locality": "Bandra",
            "budget_range": "1Cr-1.5Cr",
            "move_in_timeline": "45_days",
        },
    }

    response = client.post("/qualification/evaluate", json=payload)

    assert response.status_code == 200
    assert len(spy.updates) == 1
    lead_id, fields = spy.updates[0]
    assert lead_id == "lead_q_persist_001"
    assert fields["qualification_state"] == "fully_qualified"
    assert fields["status"] == "assigned"
    assert isinstance(fields["owner_agent_id"], str)
    assert fields["owner_agent_id"]

    app.dependency_overrides.clear()
