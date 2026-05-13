import json
from typing import Any

from google.cloud import pubsub_v1


class PubSubEventPublisher:
    def __init__(self, project_id: str, topic_id: str) -> None:
        self._publisher = pubsub_v1.PublisherClient()
        self._topic_path = self._publisher.topic_path(project_id, topic_id)

    def publish(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event).encode("utf-8")
        self._publisher.publish(self._topic_path, payload).result(timeout=10)
