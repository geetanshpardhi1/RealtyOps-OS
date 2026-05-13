# Issue #4: Qualification + Assignment Gate to Brokerage Agent

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/4
Type: AFK
Blocked by: #3
Status: Completed

## What to build
Deliver qualification behavior that classifies leads into Partially Qualified and Fully Qualified states, then assigns a Brokerage Agent only at the Assignment Gate when Partially Qualified is reached.

## Acceptance criteria
- [x] Qualification outcomes persist with canonical status transitions.
- [x] Assignment occurs only after Partially Qualified status is reached.
- [x] Assigned Brokerage Agent ownership is visible and auditable.

## Completion notes
- Added `POST /qualification/evaluate` with canonical outcomes: `unqualified`, `partially_qualified`, `fully_qualified`.
- Assignment Gate is enforced and owner assignment is stable (no reassignment churn once assigned).
- Qualification updates persist to LeadStore (`qualification_state`, `status`, `owner_agent_id`, `updated_at`).
- Qualification publishes `lead.qualified` events.
- Added auditable lead visibility endpoint: `GET /leads/{lead_id}`.
- Full API test suite passing.
