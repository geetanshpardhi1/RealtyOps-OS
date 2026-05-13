from fastapi.testclient import TestClient

from app.main import app


def test_meta_intake_accepts_unique_event() -> None:
    client = TestClient(app)

    payload = {
        "source_event_id": "evt_meta_001",
        "contact": {
            "phone": "+917777777777",
            "email": "meta@example.com",
            "first_name": "Kabir"
        },
        "preferences": {
            "preferred_locality": "Powai",
            "budget_range": "70L-90L",
            "move_in_timeline": "45_days"
        },
        "campaign": {
            "platform": "meta",
            "campaign_id": "cmp_001"
        }
    }

    response = client.post("/intake/meta", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["source"] == "meta"
    assert body["deduplicated"] is False
    assert isinstance(body["lead_id"], str)
    assert body["lead_id"]
