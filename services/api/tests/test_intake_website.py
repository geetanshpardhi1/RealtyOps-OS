from fastapi.testclient import TestClient

from app.main import app


def test_website_intake_accepts_unique_event() -> None:
    client = TestClient(app)

    payload = {
        "source_event_id": "evt_web_001",
        "contact": {
            "phone": "+919999999999",
            "email": "lead@example.com",
            "first_name": "Aarav"
        },
        "preferences": {
            "preferred_locality": "Andheri",
            "budget_range": "80L-1Cr",
            "move_in_timeline": "60_days"
        }
    }

    response = client.post("/intake/website", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["source"] == "website"
    assert body["deduplicated"] is False
    assert isinstance(body["lead_id"], str)
    assert body["lead_id"]


def test_website_intake_deduplicates_by_source_event_id() -> None:
    client = TestClient(app)

    payload = {
        "source_event_id": "evt_web_002",
        "contact": {
            "phone": "+918888888888",
            "email": "repeat@example.com",
            "first_name": "Ira"
        },
        "preferences": {
            "preferred_locality": "Bandra",
            "budget_range": "1Cr-1.5Cr",
            "move_in_timeline": "30_days"
        }
    }

    first = client.post("/intake/website", json=payload)
    second = client.post("/intake/website", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202

    first_body = first.json()
    second_body = second.json()

    assert first_body["deduplicated"] is False
    assert second_body["deduplicated"] is True
    assert first_body["lead_id"] == second_body["lead_id"]
