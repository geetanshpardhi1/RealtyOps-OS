from fastapi.testclient import TestClient

from app.main import app


def test_assignment_happens_at_partially_qualified_gate() -> None:
    client = TestClient(app)

    payload = {
        "lead_id": "lead_test_001",
        "contact": {
            "phone": "+919111111111",
            "email": "pq@example.com",
            "phone_verified": True,
            "email_verified": True,
        },
        "preferences": {
            "preferred_locality": "Andheri",
            "budget_range": None,
            "move_in_timeline": None,
        },
    }

    response = client.post("/qualification/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["qualification_state"] == "partially_qualified"
    assert body["assignment_gate_passed"] is True
    assert isinstance(body["owner_agent_id"], str)
    assert body["owner_agent_id"]


def test_fully_qualified_when_all_required_fields_present() -> None:
    client = TestClient(app)

    payload = {
        "lead_id": "lead_test_002",
        "contact": {
            "phone": "+919222222222",
            "email": "fq@example.com",
            "phone_verified": True,
            "email_verified": True,
        },
        "preferences": {
            "preferred_locality": "Bandra",
            "budget_range": "90L-1.2Cr",
            "move_in_timeline": "30_days",
        },
    }

    response = client.post("/qualification/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["qualification_state"] == "fully_qualified"
    assert body["assignment_gate_passed"] is True
    assert isinstance(body["owner_agent_id"], str)
    assert body["owner_agent_id"]


def test_unqualified_when_contact_not_reachable_or_signal_missing() -> None:
    client = TestClient(app)

    payload = {
        "lead_id": "lead_test_003",
        "contact": {
            "phone": "+919000000000",
            "email": "uq@example.com",
            "phone_verified": False,
            "email_verified": False,
        },
        "preferences": {
            "preferred_locality": "Andheri",
            "budget_range": None,
            "move_in_timeline": None,
        },
    }

    response = client.post("/qualification/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["qualification_state"] == "unqualified"
    assert body["assignment_gate_passed"] is False
    assert body["owner_agent_id"] is None
