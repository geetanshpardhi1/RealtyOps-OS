from typing import Any, Protocol


class EventPublisher(Protocol):
    def publish(self, event: dict[str, Any]) -> None:
        ...
