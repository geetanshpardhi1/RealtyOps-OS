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
