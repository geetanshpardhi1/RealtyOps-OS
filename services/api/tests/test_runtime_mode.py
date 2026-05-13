import pytest
from fastapi.testclient import TestClient

from app.main import app, get_event_publisher, get_lead_store


def test_health_reports_in_memory_mode_by_default() -> None:
    client = TestClient(app)

    response = client.get('/health')

    assert response.status_code == 200
    body = response.json()
    assert body['adapter_mode'] == 'in_memory'


def test_gcp_mode_requires_project_and_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('GCP_ENABLED', 'true')
    monkeypatch.delenv('GOOGLE_CLOUD_PROJECT', raising=False)
    monkeypatch.delenv('PUBSUB_LEAD_EVENTS_TOPIC', raising=False)

    with pytest.raises(RuntimeError):
        get_lead_store()

    with pytest.raises(RuntimeError):
        get_event_publisher()
