# Issue #11: Lifecycle Automation (auto-close/reopen + duplicate merge policy)

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/11
Type: AFK
Blocked by: #4

## What to build
Implement lifecycle automation rules for inactivity auto-close, inbound auto-reopen, and Identity Merge Rule enforcement (exact phone auto-merge, exact email when phone missing, conflict => human review).

## Locked constraints
- Lifecycle behavior updates `status` without collapsing `qualification_state`.
- Auto-reopen preserves existing Brokerage Agent ownership unless unavailable.
- Identity merge policy must evaluate against canonical Lead Contract fields, not channel-specific payload shapes.
- `automation_paused=true` blocks autonomous lifecycle actions that trigger outreach/booking side effects, but manual operations remain allowed.

## Acceptance criteria
- [x] Leads auto-close after defined inactivity window and auto-reopen on inbound reply.
- [x] Duplicate merge policy follows canonical identity rules.
- [x] Conflict identities are flagged for human review instead of blind merge.
- [x] Lifecycle transitions preserve Lead Contract state semantics.

## Completion notes
- Added lifecycle inactivity automation endpoint:
  - `POST /lifecycle/auto-close/run` with configurable inactivity window (default 14 days).
- Added inbound auto-reopen endpoint:
  - `POST /leads/{lead_id}/lifecycle/inbound-reopen`
  - Reopens closed leads while preserving existing owner assignment.
- Added identity merge policy endpoint:
  - `POST /lifecycle/identity-merge/evaluate`
  - Implements rules:
    - exact phone => auto-merge
    - exact email only when both phones are missing => auto-merge
    - otherwise => `human_review` + conflict flag on lead.
- Preserved lifecycle semantics:
  - lifecycle changes update `status` only; `qualification_state` is not collapsed.
- Added lifecycle/merge events:
  - `lead.auto_closed`, `lead.auto_reopened`, `lead.identity_conflict_flagged`.
- Added TDD coverage in `services/api/tests/test_lifecycle_automation.py`.
