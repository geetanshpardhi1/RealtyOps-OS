from fastapi.testclient import TestClient

from app.main import app


def test_assigned_brokerage_agent_is_visible_via_lead_read_endpoint() -> None:
    client = TestClient(app)

    payload = {
        "lead_id": "lead_vis_001",
        "contact": {
            "phone": "+919777777777",
            "email": "visible@example.com",
            "phone_verified": True,
            "email_verified": True,
        },
        "preferences": {
            "preferred_locality": "Powai",
            "budget_range": "80L-1Cr",
            "move_in_timeline": "45_days",
        },
    }

    qualify = client.post("/qualification/evaluate", json=payload)
    assert qualify.status_code == 200

    read = client.get("/leads/lead_vis_001")
    assert read.status_code == 200
    lead = read.json()
    assert lead["lead_id"] == "lead_vis_001"
    assert lead["status"] == "assigned"
    assert lead["qualification_state"] == "fully_qualified"
    assert isinstance(lead["owner_agent_id"], str)
    assert lead["owner_agent_id"]
