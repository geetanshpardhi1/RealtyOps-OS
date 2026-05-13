# Issue #10: CRM Mirror + Summary Notes + Outage-Decoupled Sync

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/10
Type: AFK
Blocked by: #4

## What to build
Implement HubSpot mirror sync as a decoupled flow that records summary notes, creates escalation tasks, and continues lead conversations during CRM outages via queued retries.

## Locked constraints
- CRM sync reads from canonical Lead Contract and must not introduce ad hoc lead schemas.
- Canonical fields required for sync mapping include: `lead_id`, `status`, `owner_agent_id`, `qualification_state`, `confidence`, `escalation_flags`, `booking_control_mode`, `last_activity_at`.
- Summary notes are mirrored to CRM; full transcripts remain internal.
- `status` and `qualification_state` remain separate dimensions in CRM-facing mapping.

## Acceptance criteria
- [x] CRM receives summary notes and lifecycle updates for mirrored leads.
- [x] Escalation creates CRM tasks for Brokerage Agent follow-up.
- [x] CRM outages do not block lead conversation flow and sync retries are observable.
- [x] Sync mapping preserves canonical Lead Contract semantics.

## Completion notes
- Added CRM sync endpoint:
  - `POST /leads/{lead_id}/crm/sync`
  - Mirrors canonical Lead Contract lifecycle fields and summary note only.
  - Excludes internal full transcript from CRM payload.
- Added escalation follow-up task creation in CRM sync flow (`brokerage_follow_up` task).
- Added outage-decoupled queue + retry endpoints:
  - `GET /crm/sync-queue`
  - `POST /crm/sync-queue/retry`
- Outage path returns `202` and queues sync item while conversation flow can continue.
- Added sync observability events:
  - `crm.sync_succeeded`
  - `crm.sync_queued`
  - `crm.sync_retry_executed`
- Added TDD coverage in `services/api/tests/test_crm_sync.py`.
