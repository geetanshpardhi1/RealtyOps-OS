from typing import Any


class InMemoryLeadStore:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}

    def create(self, record: dict[str, Any]) -> None:
        self.records[str(record["lead_id"])] = dict(record)

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        if lead_id not in self.records:
            self.records[lead_id] = {"lead_id": lead_id}
        self.records[lead_id].update(fields)

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        record = self.records.get(lead_id)
        return dict(record) if record else None


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)
