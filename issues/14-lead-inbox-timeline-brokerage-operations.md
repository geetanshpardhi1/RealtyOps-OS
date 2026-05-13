# Issue #14: Lead Inbox + Timeline for Brokerage Operations

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/14
Type: AFK
Blocked by: None
Status: Completed

## What to build
Deliver a Brokerage Operations Lead Inbox in the dashboard that lists Leads with filters and a per-Lead timeline so operations users can view ownership, qualification state, lifecycle status, and recent outreach/booking events without leaving the system.

## Acceptance criteria
- [x] Dashboard includes a Lead Inbox list with filters for `status`, `qualification_state`, and `owner_agent_id`.
- [x] Selecting a Lead shows a timeline with intake, qualification, outreach, booking, escalation, and lifecycle events.
- [x] UI behavior is backed by API endpoints and automated tests verifying list, filter, and timeline responses.

## Blocked by
- None - can start immediately.

## Completion notes
- Added lead inbox API endpoint:
  - `GET /leads` with filters: `status`, `qualification_state`, `owner_agent_id`.
- Added lead timeline API endpoint:
  - `GET /leads/{lead_id}/timeline`.
- Added timeline persistence support in lead stores:
  - `InMemoryLeadStore` now stores and queries timeline events.
  - `FirestoreLeadStore` now persists timeline events in `lead_events` and supports lead-scoped queries.
- Added shared event publish helper to persist timeline events while keeping Pub/Sub publishing behavior.
- Added web proxy routes to avoid browser CORS issues:
  - `GET /api/leads`
  - `GET /api/leads/[leadId]/timeline`
- Reworked dashboard UI into operations inbox + timeline layout with filters and lead selection.
- Added API tests:
  - `services/api/tests/test_lead_inbox_timeline.py`.
- Validation:
  - API tests: `44 passed`
  - Web build: `next build` successful.
