from fastapi.testclient import TestClient

from app.main import app


def test_owner_agent_is_not_reassigned_after_initial_assignment() -> None:
    client = TestClient(app)

    payload = {
        "lead_id": "lead_stable_001",
        "contact": {
            "phone": "+919888888888",
            "email": "stable@example.com",
            "phone_verified": True,
            "email_verified": True,
        },
        "preferences": {
            "preferred_locality": "Bandra",
            "budget_range": "1Cr-1.5Cr",
            "move_in_timeline": "30_days",
        },
    }

    first = client.post("/qualification/evaluate", json=payload)
    second = client.post("/qualification/evaluate", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_owner = first.json()["owner_agent_id"]
    second_owner = second.json()["owner_agent_id"]
    assert first_owner == second_owner
