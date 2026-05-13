import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeSettings:
    gcp_enabled: bool
    google_cloud_project: str | None
    firestore_database: str
    pubsub_lead_events_topic: str | None


TRUTHY = {"1", "true", "yes", "on"}


def get_runtime_settings() -> RuntimeSettings:
    gcp_enabled = os.getenv("GCP_ENABLED", "false").strip().lower() in TRUTHY
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    database = os.getenv("FIRESTORE_DATABASE", "(default)")
    topic = os.getenv("PUBSUB_LEAD_EVENTS_TOPIC")

    if gcp_enabled:
        if not project:
            raise RuntimeError("GCP_ENABLED=true but GOOGLE_CLOUD_PROJECT is missing")
        if not topic:
            raise RuntimeError("GCP_ENABLED=true but PUBSUB_LEAD_EVENTS_TOPIC is missing")

    return RuntimeSettings(
        gcp_enabled=gcp_enabled,
        google_cloud_project=project,
        firestore_database=database,
        pubsub_lead_events_topic=topic,
    )


def get_adapter_mode() -> str:
    settings = get_runtime_settings()
    return "gcp" if settings.gcp_enabled else "in_memory"


def validate_runtime_settings() -> RuntimeSettings:
    return get_runtime_settings()
