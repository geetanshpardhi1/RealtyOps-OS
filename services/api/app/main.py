from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import logging

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from app.adapters.firestore_lead_store import FirestoreLeadStore
from app.adapters.in_memory import InMemoryEventPublisher, InMemoryLeadStore
from app.adapters.pubsub_event_publisher import PubSubEventPublisher
from app.core.runtime import get_adapter_mode, get_runtime_settings, validate_runtime_settings
from app.ports.event_publisher import EventPublisher
from app.ports.lead_store import LeadStore

logger = logging.getLogger("realtyops.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = validate_runtime_settings()
    logger.info(
        "runtime_config_validated",
        extra={"adapter_mode": "gcp" if settings.gcp_enabled else "in_memory"},
    )
    yield


app = FastAPI(title="RealtyOps API", version="0.1.0", lifespan=lifespan)

# Temporary in-memory idempotency cache for bootstrap TDD cycle.
# In a later issue, this will move to persistent storage for distributed safety.
_seen_source_events: dict[str, str] = {}

_default_lead_store = InMemoryLeadStore()
_default_event_publisher = InMemoryEventPublisher()

_ASSIGNABLE_BROKERAGE_AGENTS = ["agent_001", "agent_002", "agent_003"]
_assignment_index = 0
_slot_proposals_by_lead: dict[str, dict[str, Any]] = {}
_slot_confirmations: dict[str, str] = {}


class WhatsAppSender:
    def send_first_touch(self, lead_id: str, phone: str, first_name: str) -> str:
        return "delivered"


class EmailSender:
    def send_first_touch(self, lead_id: str, email: str, first_name: str) -> str:
        return "sent"


_default_whatsapp_sender = WhatsAppSender()
_default_email_sender = EmailSender()


class CalendarWriter:
    def create_tour_event(self, lead_id: str, slot: str) -> tuple[str, str | None]:
        return ("success", f"gcal_evt_{lead_id}")


_default_calendar_writer = CalendarWriter()
_crm_sync_queue: list[dict[str, Any]] = []


def get_lead_store() -> LeadStore:
    settings = get_runtime_settings()
    if settings.gcp_enabled:
        return FirestoreLeadStore(
            project_id=settings.google_cloud_project or "",
            database=settings.firestore_database,
        )
    return _default_lead_store


def get_event_publisher() -> EventPublisher:
    settings = get_runtime_settings()
    if settings.gcp_enabled:
        return PubSubEventPublisher(
            project_id=settings.google_cloud_project or "",
            topic_id=settings.pubsub_lead_events_topic or "",
        )
    return _default_event_publisher


def get_whatsapp_sender() -> WhatsAppSender:
    return _default_whatsapp_sender


def get_email_sender() -> EmailSender:
    return _default_email_sender


def get_calendar_writer() -> CalendarWriter:
    return _default_calendar_writer


class CRMClient:
    def upsert_lead(self, payload: dict[str, Any]) -> str:
        return f"crm_{payload['lead_id']}"

    def create_task(self, payload: dict[str, Any]) -> str:
        return f"crm_task_{payload['lead_id']}"


_default_crm_client = CRMClient()


def get_crm_client() -> CRMClient:
    return _default_crm_client


class ContactPayload(BaseModel):
    phone: str
    email: EmailStr
    first_name: str


class PreferencesPayload(BaseModel):
    preferred_locality: str
    budget_range: str
    move_in_timeline: str


class CampaignPayload(BaseModel):
    platform: str
    campaign_id: str


class WebsiteIntakePayload(BaseModel):
    source_event_id: str
    contact: ContactPayload
    preferences: PreferencesPayload


class MetaIntakePayload(BaseModel):
    source_event_id: str
    contact: ContactPayload
    preferences: PreferencesPayload
    campaign: CampaignPayload


class QualificationContactPayload(BaseModel):
    phone: str
    email: EmailStr
    phone_verified: bool
    email_verified: bool


class QualificationPreferencesPayload(BaseModel):
    preferred_locality: str | None = None
    budget_range: str | None = None
    move_in_timeline: str | None = None


class QualificationRequest(BaseModel):
    lead_id: str
    contact: QualificationContactPayload
    preferences: QualificationPreferencesPayload


class QualificationResponse(BaseModel):
    lead_id: str
    qualification_state: str
    assignment_gate_passed: bool
    owner_agent_id: str | None


class OutreachFirstTouchRequest(BaseModel):
    lead_id: str
    phone: str
    email: EmailStr
    first_name: str


class OutreachFirstTouchResponse(BaseModel):
    lead_id: str
    primary_channel: str
    whatsapp_outcome: str
    email_fallback_triggered: bool
    email_outcome: str | None = None


class LeadAutomationStateResponse(BaseModel):
    lead_id: str
    automation_paused: bool


class ManualTakeoverRequest(BaseModel):
    actor_user_id: str
    actor_role: str


class ManualTakeoverResponse(BaseModel):
    lead_id: str
    booking_control_mode: str
    assist_mode: str
    takeover_at: str
    checkpoint_at: str


class CadenceContinuityRequest(BaseModel):
    continuity_approved: bool
    actor_user_id: str
    actor_role: str


class CadenceContinuityResponse(BaseModel):
    lead_id: str
    continuity_approved: bool


class SlotProposalRequest(BaseModel):
    cycle: int
    candidate_slots: list[str] = Field(min_length=3, max_length=3)


class SlotProposalResponse(BaseModel):
    lead_id: str
    cycle: int
    proposed_slots: list[str]


class SlotConfirmRequest(BaseModel):
    slot: str
    cycle: int
    candidate_slots: list[str] = Field(min_length=3, max_length=3)


class SlotConfirmResponse(BaseModel):
    lead_id: str
    cycle: int
    status: str
    confirmed_slot: str | None = None
    winner_lead_id: str | None = None
    alternative_slots: list[str] = []


class BookingAttemptRequest(BaseModel):
    slot: str
    fallback_slots: list[str] = []


class BookingAttemptResponse(BaseModel):
    lead_id: str
    status: str
    confirmed: bool
    calendar_event_id: str | None = None
    recommended_slots: list[str] = []


class EscalationEvaluateResponse(BaseModel):
    lead_id: str
    booking_escalated: bool
    booking_control_mode: str
    reasons: list[str]


class OutreachContinuationPlanResponse(BaseModel):
    lead_id: str
    active: bool
    scheduled_touchpoints: list[str]


class CRMSyncRequest(BaseModel):
    summary_note: str
    create_escalation_task: bool = False


class CRMSyncResponse(BaseModel):
    lead_id: str
    synced: bool
    queued: bool


class CRMSyncQueueResponse(BaseModel):
    queued_count: int


class CRMSyncRetryResponse(BaseModel):
    retried: int


class AutoCloseRunRequest(BaseModel):
    inactivity_days: int = 14


class AutoCloseRunResponse(BaseModel):
    closed_count: int


class InboundReopenResponse(BaseModel):
    lead_id: str
    reopened: bool


class IdentityContact(BaseModel):
    phone: str | None = None
    email: str | None = None


class IdentityMergeEvaluateRequest(BaseModel):
    lead_id: str
    incoming: IdentityContact


class IdentityMergeEvaluateResponse(BaseModel):
    lead_id: str
    decision: str
    reason: str


class CorrelationLogRequest(BaseModel):
    lead_id: str
    event_type: str


class CorrelationLogResponse(BaseModel):
    lead_id: str
    event_id: str
    correlation_id: str


class DailyKPIResponse(BaseModel):
    lead_count: int
    first_response_time_minutes: float
    follow_up_completion_rate: float
    tours_per_100_leads: float


class AlertItem(BaseModel):
    name: str
    severity: str
    value: float


class AlertsEvaluateResponse(BaseModel):
    alerts: list[AlertItem]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api", "adapter_mode": get_adapter_mode()}


@app.get("/config")
def config() -> dict[str, str]:
    settings = get_runtime_settings()
    return {
        "adapter_mode": "gcp" if settings.gcp_enabled else "in_memory",
        "gcp_enabled": str(settings.gcp_enabled).lower(),
        "firestore_database": settings.firestore_database,
        "pubsub_topic": settings.pubsub_lead_events_topic or "",
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "RealtyOps API bootstrap"}


@app.get("/leads/{lead_id}")
def get_lead(lead_id: str, lead_store: LeadStore = Depends(get_lead_store)) -> dict[str, Any]:
    record = lead_store.get_by_id(lead_id)
    if record is None:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return record


def _build_lead_contract(lead_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "lead_id": lead_id,
        "status": "new",
        "owner_agent_id": None,
        "qualification_state": "unqualified",
        "confidence": 0.0,
        "escalation_flags": {
            "missing_fields": False,
            "low_confidence": False,
            "conflict": False,
            "complex_query": False,
            "callback_requested": False,
        },
        "booking_control_mode": "autonomous",
        "automation_paused": False,
        "last_activity_at": now,
        "created_at": now,
        "updated_at": now,
    }


def _accept_intake(
    source_event_id: str,
    source: str,
    lead_store: LeadStore,
    event_publisher: EventPublisher,
) -> dict[str, str | bool]:
    if source_event_id in _seen_source_events:
        return {
            "accepted": True,
            "source": source,
            "deduplicated": True,
            "lead_id": _seen_source_events[source_event_id],
        }

    lead_id = f"lead_{uuid4().hex[:12]}"
    _seen_source_events[source_event_id] = lead_id

    lead_store.create(_build_lead_contract(lead_id))
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "lead.created",
            "lead_id": lead_id,
            "source": source,
            "idempotency_key": source_event_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return {
        "accepted": True,
        "source": source,
        "deduplicated": False,
        "lead_id": lead_id,
    }


def _next_brokerage_agent_id() -> str:
    global _assignment_index
    agent_id = _ASSIGNABLE_BROKERAGE_AGENTS[_assignment_index % len(_ASSIGNABLE_BROKERAGE_AGENTS)]
    _assignment_index += 1
    return agent_id


def _evaluate_qualification(payload: QualificationRequest, existing_owner_agent_id: str | None) -> QualificationResponse:
    has_reachable_contact = payload.contact.phone_verified or payload.contact.email_verified
    has_any_signal = bool(
        payload.preferences.preferred_locality
        or payload.preferences.budget_range
        or payload.preferences.move_in_timeline
    )

    assignment_gate_passed = has_reachable_contact and has_any_signal

    is_fully_qualified = bool(
        has_reachable_contact
        and payload.preferences.preferred_locality
        and payload.preferences.budget_range
        and payload.preferences.move_in_timeline
    )

    qualification_state = (
        "fully_qualified"
        if is_fully_qualified
        else ("partially_qualified" if assignment_gate_passed else "unqualified")
    )

    if assignment_gate_passed:
        owner_agent_id = existing_owner_agent_id or _next_brokerage_agent_id()
    else:
        owner_agent_id = None

    return QualificationResponse(
        lead_id=payload.lead_id,
        qualification_state=qualification_state,
        assignment_gate_passed=assignment_gate_passed,
        owner_agent_id=owner_agent_id,
    )


@app.post("/qualification/evaluate", response_model=QualificationResponse)
def qualification_evaluate(
    payload: QualificationRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> QualificationResponse:
    existing = lead_store.get_by_id(payload.lead_id) or {}
    existing_owner_agent_id = existing.get("owner_agent_id")

    outcome = _evaluate_qualification(payload, existing_owner_agent_id)

    lead_store.update_fields(
        payload.lead_id,
        {
            "qualification_state": outcome.qualification_state,
            "status": "assigned" if outcome.assignment_gate_passed else "qualifying",
            "owner_agent_id": outcome.owner_agent_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "lead.qualified",
            "lead_id": payload.lead_id,
            "qualification_state": outcome.qualification_state,
            "assignment_gate_passed": outcome.assignment_gate_passed,
            "owner_agent_id": outcome.owner_agent_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return outcome


@app.post("/intake/website", status_code=202)
def intake_website(
    payload: WebsiteIntakePayload,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> dict[str, str | bool]:
    return _accept_intake(payload.source_event_id, "website", lead_store, event_publisher)


@app.post("/intake/meta", status_code=202)
def intake_meta(
    payload: MetaIntakePayload,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> dict[str, str | bool]:
    return _accept_intake(payload.source_event_id, "meta", lead_store, event_publisher)


@app.post("/outreach/first-touch", response_model=OutreachFirstTouchResponse)
def outreach_first_touch(
    payload: OutreachFirstTouchRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
    whatsapp_sender: WhatsAppSender = Depends(get_whatsapp_sender),
    email_sender: EmailSender = Depends(get_email_sender),
) -> OutreachFirstTouchResponse:
    lead = lead_store.get_by_id(payload.lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")

    qualification_state = str(lead.get("qualification_state", "unqualified"))
    if qualification_state not in {"partially_qualified", "fully_qualified"}:
        raise HTTPException(status_code=409, detail="lead_not_eligible_for_outreach")
    if bool(lead.get("automation_paused", False)):
        raise HTTPException(status_code=409, detail="automation_paused")

    whatsapp_outcome = whatsapp_sender.send_first_touch(
        payload.lead_id, payload.phone, payload.first_name
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "outreach.attempted",
            "lead_id": payload.lead_id,
            "channel": "whatsapp",
            "delivery_outcome": whatsapp_outcome,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    should_fallback = whatsapp_outcome in {"failed", "undelivered"}
    email_outcome: str | None = None
    if should_fallback:
        email_outcome = email_sender.send_first_touch(
            payload.lead_id, str(payload.email), payload.first_name
        )
        event_publisher.publish(
            {
                "event_id": f"evt_{uuid4().hex[:12]}",
                "event_type": "outreach.attempted",
                "lead_id": payload.lead_id,
                "channel": "email",
                "delivery_outcome": email_outcome,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return OutreachFirstTouchResponse(
        lead_id=payload.lead_id,
        primary_channel="whatsapp",
        whatsapp_outcome=whatsapp_outcome,
        email_fallback_triggered=should_fallback,
        email_outcome=email_outcome,
    )


@app.post("/leads/{lead_id}/automation/pause", response_model=LeadAutomationStateResponse)
def pause_automation(
    lead_id: str,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> LeadAutomationStateResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")

    lead_store.update_fields(
        lead_id,
        {
            "automation_paused": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "lead.automation_paused",
            "lead_id": lead_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return LeadAutomationStateResponse(lead_id=lead_id, automation_paused=True)


@app.post("/leads/{lead_id}/automation/resume", response_model=LeadAutomationStateResponse)
def resume_automation(
    lead_id: str,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> LeadAutomationStateResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")

    lead_store.update_fields(
        lead_id,
        {
            "automation_paused": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "lead.automation_resumed",
            "lead_id": lead_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return LeadAutomationStateResponse(lead_id=lead_id, automation_paused=False)


@app.post("/leads/{lead_id}/takeover", response_model=ManualTakeoverResponse)
def manual_takeover(
    lead_id: str,
    payload: ManualTakeoverRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> ManualTakeoverResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")
    if payload.actor_role not in {"brokerage_agent", "admin"}:
        raise HTTPException(status_code=403, detail="insufficient_permissions")

    now = datetime.now(timezone.utc)
    checkpoint_at = now + timedelta(hours=72)
    lead_store.update_fields(
        lead_id,
        {
            "booking_control_mode": "brokerage_controlled",
            "assist_mode": "draft_only",
            "takeover_at": now.isoformat(),
            "takeover_checkpoint_at": checkpoint_at.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "lead.manual_takeover_enabled",
            "lead_id": lead_id,
            "actor_user_id": payload.actor_user_id,
            "actor_role": payload.actor_role,
            "assist_mode": "draft_only",
            "checkpoint_at": checkpoint_at.isoformat(),
            "occurred_at": now.isoformat(),
        }
    )
    return ManualTakeoverResponse(
        lead_id=lead_id,
        booking_control_mode="brokerage_controlled",
        assist_mode="draft_only",
        takeover_at=now.isoformat(),
        checkpoint_at=checkpoint_at.isoformat(),
    )


@app.post("/leads/{lead_id}/cadence-continuity", response_model=CadenceContinuityResponse)
def set_cadence_continuity(
    lead_id: str,
    payload: CadenceContinuityRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> CadenceContinuityResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")
    if payload.actor_role not in {"brokerage_agent", "admin"}:
        raise HTTPException(status_code=403, detail="insufficient_permissions")

    lead_store.update_fields(
        lead_id,
        {
            "cadence_continuity_approved": payload.continuity_approved,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "lead.cadence_continuity_changed",
            "lead_id": lead_id,
            "continuity_approved": payload.continuity_approved,
            "actor_user_id": payload.actor_user_id,
            "actor_role": payload.actor_role,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return CadenceContinuityResponse(
        lead_id=lead_id,
        continuity_approved=payload.continuity_approved,
    )


@app.post("/leads/{lead_id}/slot-negotiation/propose", response_model=SlotProposalResponse)
def propose_slots(
    lead_id: str,
    payload: SlotProposalRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> SlotProposalResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")
    if payload.cycle > 2:
        raise HTTPException(status_code=409, detail="max_cycles_exceeded")

    _slot_proposals_by_lead[lead_id] = {
        "cycle": payload.cycle,
        "proposed_slots": list(payload.candidate_slots),
    }
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "slot.proposed",
            "lead_id": lead_id,
            "cycle": payload.cycle,
            "proposed_slots": list(payload.candidate_slots),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return SlotProposalResponse(
        lead_id=lead_id,
        cycle=payload.cycle,
        proposed_slots=list(payload.candidate_slots),
    )


@app.post("/leads/{lead_id}/slot-negotiation/confirm", response_model=SlotConfirmResponse)
def confirm_slot(
    lead_id: str,
    payload: SlotConfirmRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> SlotConfirmResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")
    if payload.cycle > 2:
        raise HTTPException(status_code=409, detail="max_cycles_exceeded")

    winner = _slot_confirmations.get(payload.slot)
    if winner is None or winner == lead_id:
        _slot_confirmations[payload.slot] = lead_id
        event_publisher.publish(
            {
                "event_id": f"evt_{uuid4().hex[:12]}",
                "event_type": "slot.confirmed",
                "lead_id": lead_id,
                "cycle": payload.cycle,
                "slot": payload.slot,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return SlotConfirmResponse(
            lead_id=lead_id,
            cycle=payload.cycle,
            status="confirmed",
            confirmed_slot=payload.slot,
        )

    alternatives = [
        slot
        for slot in payload.candidate_slots
        if slot != payload.slot and _slot_confirmations.get(slot) in {None, lead_id}
    ]
    if not alternatives:
        alternatives = [f"{payload.slot}#alt1", f"{payload.slot}#alt2", f"{payload.slot}#alt3"]

    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "slot.collision",
            "lead_id": lead_id,
            "cycle": payload.cycle,
            "slot": payload.slot,
            "winner_lead_id": winner,
            "alternative_slots": alternatives,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return SlotConfirmResponse(
        lead_id=lead_id,
        cycle=payload.cycle,
        status="collision",
        winner_lead_id=winner,
        alternative_slots=alternatives,
    )


def _autonomous_booking_gate_passed(lead: dict[str, Any]) -> bool:
    if str(lead.get("qualification_state", "")) != "fully_qualified":
        return False
    if float(lead.get("confidence", 0.0)) < 0.80:
        return False
    escalation_flags = lead.get("escalation_flags") or {}
    return not any(bool(v) for v in escalation_flags.values())


def _escalation_reasons(lead: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    confidence = float(lead.get("confidence", 0.0))
    if confidence < 0.70:
        reasons.append("low_confidence")
    elif confidence < 0.80:
        reasons.append("borderline_confidence")

    escalation_flags = lead.get("escalation_flags") or {}
    for key in ("missing_fields", "conflict", "complex_query", "callback_requested"):
        if bool(escalation_flags.get(key, False)):
            reasons.append(key)
    return reasons


def _build_crm_lead_payload(lead: dict[str, Any], summary_note: str) -> dict[str, Any]:
    # Preserve canonical Lead Contract semantics: status and qualification_state remain separate.
    return {
        "lead_id": lead.get("lead_id"),
        "status": lead.get("status"),
        "owner_agent_id": lead.get("owner_agent_id"),
        "qualification_state": lead.get("qualification_state"),
        "confidence": lead.get("confidence"),
        "escalation_flags": lead.get("escalation_flags"),
        "booking_control_mode": lead.get("booking_control_mode"),
        "last_activity_at": lead.get("last_activity_at"),
        "summary_note": summary_note,
    }


def _iter_leads_for_lifecycle(lead_store: LeadStore) -> list[dict[str, Any]]:
    records = getattr(lead_store, "records", None)
    if isinstance(records, dict):
        return [dict(v) for v in records.values()]
    return []


def _iter_events(event_publisher: EventPublisher) -> list[dict[str, Any]]:
    events = getattr(event_publisher, "events", None)
    if isinstance(events, list):
        return [dict(e) for e in events]
    return []


@app.post("/leads/{lead_id}/escalation/evaluate", response_model=EscalationEvaluateResponse)
def evaluate_escalation(
    lead_id: str,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> EscalationEvaluateResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")

    reasons = _escalation_reasons(lead)
    booking_escalated = len(reasons) > 0
    booking_control_mode = "brokerage_controlled" if booking_escalated else "autonomous"

    lead_store.update_fields(
        lead_id,
        {
            "booking_escalated": booking_escalated,
            "booking_escalation_reasons": reasons,
            "booking_control_mode": booking_control_mode,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "lead.booking_escalation_evaluated",
            "lead_id": lead_id,
            "booking_escalated": booking_escalated,
            "reasons": reasons,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return EscalationEvaluateResponse(
        lead_id=lead_id,
        booking_escalated=booking_escalated,
        booking_control_mode=booking_control_mode,
        reasons=reasons,
    )


@app.post("/leads/{lead_id}/outreach/continuation/plan", response_model=OutreachContinuationPlanResponse)
def outreach_continuation_plan(
    lead_id: str,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> OutreachContinuationPlanResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")

    paused = bool(lead.get("automation_paused", False))
    active = bool(lead.get("booking_escalated", False)) and not paused
    touchpoints = ["T+24h", "T+72h"] if active else []
    lead_store.update_fields(
        lead_id,
        {
            "outreach_continuation_active": active,
            "outreach_continuation_touchpoints": touchpoints,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "outreach.continuation_planned",
            "lead_id": lead_id,
            "active": active,
            "scheduled_touchpoints": touchpoints,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return OutreachContinuationPlanResponse(
        lead_id=lead_id,
        active=active,
        scheduled_touchpoints=touchpoints,
    )


@app.post("/leads/{lead_id}/booking/attempt", response_model=BookingAttemptResponse)
def attempt_booking(
    lead_id: str,
    payload: BookingAttemptRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
    calendar_writer: CalendarWriter = Depends(get_calendar_writer),
) -> BookingAttemptResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")
    if bool(lead.get("booking_escalated", False)) or str(lead.get("booking_control_mode", "")) == "brokerage_controlled":
        raise HTTPException(status_code=409, detail="booking_escalated_human_control_required")
    if not _autonomous_booking_gate_passed(lead):
        raise HTTPException(status_code=409, detail="autonomous_booking_gate_failed")

    now = datetime.now(timezone.utc).isoformat()
    lead_store.update_fields(
        lead_id,
        {"booking_status": "in_progress", "updated_at": now},
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "booking.in_progress",
            "lead_id": lead_id,
            "slot": payload.slot,
            "occurred_at": now,
        }
    )

    first_outcome, first_event_id = calendar_writer.create_tour_event(lead_id, payload.slot)
    if first_outcome == "success" and first_event_id:
        lead_store.update_fields(
            lead_id,
            {"status": "booked", "booking_status": "confirmed", "calendar_event_id": first_event_id, "updated_at": datetime.now(timezone.utc).isoformat()},
        )
        event_publisher.publish(
            {
                "event_id": f"evt_{uuid4().hex[:12]}",
                "event_type": "booking.confirmed",
                "lead_id": lead_id,
                "slot": payload.slot,
                "calendar_event_id": first_event_id,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return BookingAttemptResponse(
            lead_id=lead_id,
            status="confirmed",
            confirmed=True,
            calendar_event_id=first_event_id,
        )

    if payload.fallback_slots:
        second_outcome, second_event_id = calendar_writer.create_tour_event(lead_id, payload.fallback_slots[0])
        if second_outcome == "success" and second_event_id:
            lead_store.update_fields(
                lead_id,
                {
                    "status": "booked",
                    "booking_status": "confirmed",
                    "calendar_event_id": second_event_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            event_publisher.publish(
                {
                    "event_id": f"evt_{uuid4().hex[:12]}",
                    "event_type": "booking.confirmed",
                    "lead_id": lead_id,
                    "slot": payload.fallback_slots[0],
                    "calendar_event_id": second_event_id,
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            return BookingAttemptResponse(
                lead_id=lead_id,
                status="confirmed",
                confirmed=True,
                calendar_event_id=second_event_id,
            )

    lead_store.update_fields(
        lead_id,
        {"status": "assigned", "booking_status": "retry_required", "updated_at": datetime.now(timezone.utc).isoformat()},
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "booking.failed",
            "lead_id": lead_id,
            "slot": payload.slot,
            "failure_outcome": first_outcome,
            "recommended_slots": payload.fallback_slots,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return BookingAttemptResponse(
        lead_id=lead_id,
        status="retry_required",
        confirmed=False,
        recommended_slots=payload.fallback_slots,
    )


@app.post("/leads/{lead_id}/crm/sync", response_model=CRMSyncResponse, status_code=200)
def sync_lead_to_crm(
    lead_id: str,
    payload: CRMSyncRequest,
    response: Response,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
    crm_client: CRMClient = Depends(get_crm_client),
) -> CRMSyncResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")

    crm_payload = _build_crm_lead_payload(lead, payload.summary_note)
    queue_item = {
        "lead_id": lead_id,
        "crm_payload": crm_payload,
        "create_escalation_task": payload.create_escalation_task,
        "task_payload": {
            "lead_id": lead_id,
            "owner_agent_id": lead.get("owner_agent_id"),
            "type": "brokerage_follow_up",
            "summary_note": payload.summary_note,
        },
    }

    try:
        crm_client.upsert_lead(crm_payload)
        if payload.create_escalation_task:
            crm_client.create_task(queue_item["task_payload"])
        event_publisher.publish(
            {
                "event_id": f"evt_{uuid4().hex[:12]}",
                "event_type": "crm.sync_succeeded",
                "lead_id": lead_id,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return CRMSyncResponse(lead_id=lead_id, synced=True, queued=False)
    except Exception:
        response.status_code = 202
        _crm_sync_queue.append(queue_item)
        event_publisher.publish(
            {
                "event_id": f"evt_{uuid4().hex[:12]}",
                "event_type": "crm.sync_queued",
                "lead_id": lead_id,
                "queue_size": len(_crm_sync_queue),
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return CRMSyncResponse(lead_id=lead_id, synced=False, queued=True)


@app.get("/crm/sync-queue", response_model=CRMSyncQueueResponse)
def get_crm_sync_queue() -> CRMSyncQueueResponse:
    return CRMSyncQueueResponse(queued_count=len(_crm_sync_queue))


@app.post("/crm/sync-queue/retry", response_model=CRMSyncRetryResponse)
def retry_crm_sync_queue(
    crm_client: CRMClient = Depends(get_crm_client),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> CRMSyncRetryResponse:
    retried = 0
    remaining: list[dict[str, Any]] = []
    for item in _crm_sync_queue:
        retried += 1
        try:
            crm_client.upsert_lead(item["crm_payload"])
            if item["create_escalation_task"]:
                crm_client.create_task(item["task_payload"])
        except Exception:
            remaining.append(item)
    _crm_sync_queue.clear()
    _crm_sync_queue.extend(remaining)
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "crm.sync_retry_executed",
            "retried": retried,
            "remaining": len(_crm_sync_queue),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return CRMSyncRetryResponse(retried=retried)


@app.post("/lifecycle/auto-close/run", response_model=AutoCloseRunResponse)
def lifecycle_auto_close_run(
    payload: AutoCloseRunRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> AutoCloseRunResponse:
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=payload.inactivity_days)
    closed_count = 0
    for lead in _iter_leads_for_lifecycle(lead_store):
        if str(lead.get("status")) == "closed":
            continue
        last_activity_raw = lead.get("last_activity_at")
        if not isinstance(last_activity_raw, str):
            continue
        try:
            last_activity = datetime.fromisoformat(last_activity_raw)
        except ValueError:
            continue
        if last_activity < threshold:
            lead_id = str(lead["lead_id"])
            lead_store.update_fields(
                lead_id,
                {"status": "closed", "updated_at": now.isoformat()},
            )
            event_publisher.publish(
                {
                    "event_id": f"evt_{uuid4().hex[:12]}",
                    "event_type": "lead.auto_closed",
                    "lead_id": lead_id,
                    "occurred_at": now.isoformat(),
                }
            )
            closed_count += 1
    return AutoCloseRunResponse(closed_count=closed_count)


@app.post("/leads/{lead_id}/lifecycle/inbound-reopen", response_model=InboundReopenResponse)
def lifecycle_inbound_reopen(
    lead_id: str,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> InboundReopenResponse:
    lead = lead_store.get_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")

    reopened = str(lead.get("status")) == "closed"
    if reopened:
        lead_store.update_fields(
            lead_id,
            {
                "status": "assigned",
                "last_activity_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        event_publisher.publish(
            {
                "event_id": f"evt_{uuid4().hex[:12]}",
                "event_type": "lead.auto_reopened",
                "lead_id": lead_id,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return InboundReopenResponse(lead_id=lead_id, reopened=reopened)


@app.post("/lifecycle/identity-merge/evaluate", response_model=IdentityMergeEvaluateResponse)
def lifecycle_identity_merge_evaluate(
    payload: IdentityMergeEvaluateRequest,
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> IdentityMergeEvaluateResponse:
    lead = lead_store.get_by_id(payload.lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")

    contact = lead.get("contact") or {}
    existing_phone = (contact.get("phone") or "").strip()
    existing_email = (contact.get("email") or "").strip().lower()
    incoming_phone = (payload.incoming.phone or "").strip()
    incoming_email = (payload.incoming.email or "").strip().lower()

    if existing_phone and incoming_phone and existing_phone == incoming_phone:
        return IdentityMergeEvaluateResponse(
            lead_id=payload.lead_id,
            decision="auto_merge",
            reason="exact_phone_match",
        )

    if not existing_phone and not incoming_phone and existing_email and incoming_email and existing_email == incoming_email:
        return IdentityMergeEvaluateResponse(
            lead_id=payload.lead_id,
            decision="auto_merge",
            reason="exact_email_match_phone_missing",
        )

    updated_flags = dict(lead.get("escalation_flags") or {})
    updated_flags["conflict"] = True
    lead_store.update_fields(
        payload.lead_id,
        {"escalation_flags": updated_flags, "updated_at": datetime.now(timezone.utc).isoformat()},
    )
    event_publisher.publish(
        {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": "lead.identity_conflict_flagged",
            "lead_id": payload.lead_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return IdentityMergeEvaluateResponse(
        lead_id=payload.lead_id,
        decision="human_review",
        reason="identity_conflict",
    )


@app.post("/observability/correlation-log", response_model=CorrelationLogResponse)
def observability_correlation_log(
    payload: CorrelationLogRequest,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> CorrelationLogResponse:
    lead = lead_store.get_by_id(payload.lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")
    corr = correlation_id or f"corr_{uuid4().hex[:10]}"
    event_id = f"evt_{uuid4().hex[:12]}"
    logger.info(
        "structured_observability_event",
        extra={
            "lead_id": payload.lead_id,
            "event_id": event_id,
            "correlation_id": corr,
            "event_type": payload.event_type,
        },
    )
    event_publisher.publish(
        {
            "event_id": event_id,
            "event_type": payload.event_type,
            "lead_id": payload.lead_id,
            "correlation_id": corr,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return CorrelationLogResponse(
        lead_id=payload.lead_id,
        event_id=event_id,
        correlation_id=corr,
    )


@app.get("/observability/kpi/daily", response_model=DailyKPIResponse)
def observability_kpi_daily(
    lead_store: LeadStore = Depends(get_lead_store),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> DailyKPIResponse:
    leads = _iter_leads_for_lifecycle(lead_store)
    events = _iter_events(event_publisher)

    created_by_lead: dict[str, datetime] = {}
    first_outreach_by_lead: dict[str, datetime] = {}
    followup_completed_leads: set[str] = set()
    tours_confirmed = 0
    for event in events:
        event_type = str(event.get("event_type", ""))
        lead_id = str(event.get("lead_id", ""))
        occurred_at_raw = event.get("occurred_at")
        if not isinstance(occurred_at_raw, str):
            continue
        try:
            occurred_at = datetime.fromisoformat(occurred_at_raw)
        except ValueError:
            continue

        if event_type == "lead.created":
            created_by_lead[lead_id] = occurred_at
        elif event_type == "outreach.attempted":
            current = first_outreach_by_lead.get(lead_id)
            if current is None or occurred_at < current:
                first_outreach_by_lead[lead_id] = occurred_at
        elif event_type == "outreach.continuation_planned" and bool(event.get("active", False)):
            followup_completed_leads.add(lead_id)
        elif event_type == "booking.confirmed":
            tours_confirmed += 1

    response_minutes: list[float] = []
    for lead_id, created_at in created_by_lead.items():
        first_touch = first_outreach_by_lead.get(lead_id)
        if first_touch is not None and first_touch >= created_at:
            response_minutes.append((first_touch - created_at).total_seconds() / 60.0)

    lead_count = len(leads)
    first_response_time_minutes = round(sum(response_minutes) / len(response_minutes), 2) if response_minutes else 0.0
    follow_up_completion_rate = round(len(followup_completed_leads) / lead_count, 2) if lead_count else 0.0
    tours_per_100 = round((tours_confirmed / lead_count) * 100.0, 2) if lead_count else 0.0

    return DailyKPIResponse(
        lead_count=lead_count,
        first_response_time_minutes=first_response_time_minutes,
        follow_up_completion_rate=follow_up_completion_rate,
        tours_per_100_leads=tours_per_100,
    )


@app.get("/observability/alerts/evaluate", response_model=AlertsEvaluateResponse)
def observability_alerts_evaluate(
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> AlertsEvaluateResponse:
    events = _iter_events(event_publisher)
    webhook_failed_count = sum(1 for e in events if e.get("event_type") == "webhook.failed")
    booking_failed_count = sum(1 for e in events if e.get("event_type") == "booking.failed")
    dlq_growth_total = float(sum(float(e.get("delta", 0)) for e in events if e.get("event_type") == "dlq.growth"))

    alerts: list[AlertItem] = []
    if webhook_failed_count >= 2:
        alerts.append(AlertItem(name="webhook_failures", severity="critical", value=float(webhook_failed_count)))
    if dlq_growth_total >= 5:
        alerts.append(AlertItem(name="dlq_growth", severity="critical", value=dlq_growth_total))
    if booking_failed_count >= 3:
        alerts.append(AlertItem(name="booking_failures", severity="critical", value=float(booking_failed_count)))
    return AlertsEvaluateResponse(alerts=alerts)
