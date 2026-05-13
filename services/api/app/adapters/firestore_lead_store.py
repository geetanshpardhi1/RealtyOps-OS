from typing import Any

from google.cloud import firestore


class FirestoreLeadStore:
    def __init__(self, project_id: str, database: str = "(default)") -> None:
        self._client = firestore.Client(project=project_id, database=database)

    def create(self, record: dict[str, Any]) -> None:
        lead_id = str(record["lead_id"])
        self._client.collection("leads").document(lead_id).set(record)

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        self._client.collection("leads").document(lead_id).set(fields, merge=True)

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        snapshot = self._client.collection("leads").document(lead_id).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        if "lead_id" not in data:
            data["lead_id"] = lead_id
        return data

    def list_leads(self) -> list[dict[str, Any]]:
        docs = self._client.collection("leads").stream()
        leads: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            if "lead_id" not in data:
                data["lead_id"] = doc.id
            leads.append(data)
        return leads

    def append_event(self, event: dict[str, Any]) -> None:
        event_id = str(event.get("event_id") or f"evt_{event.get('lead_id', 'unknown')}")
        self._client.collection("lead_events").document(event_id).set(dict(event))

    def list_events(self, lead_id: str, limit: int = 100) -> list[dict[str, Any]]:
        base = self._client.collection("lead_events")
        if lead_id:
            query = (
                base.where("lead_id", "==", lead_id)
                .order_by("occurred_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
        else:
            query = base.order_by("occurred_at", direction=firestore.Query.DESCENDING).limit(limit)
        events: list[dict[str, Any]] = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            if "event_id" not in data:
                data["event_id"] = doc.id
            events.append(data)
        return events
