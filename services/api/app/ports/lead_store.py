from typing import Any, Protocol


class LeadStore(Protocol):
    def create(self, record: dict[str, Any]) -> None:
        ...

    def update_fields(self, lead_id: str, fields: dict[str, Any]) -> None:
        ...

    def get_by_id(self, lead_id: str) -> dict[str, Any] | None:
        ...
