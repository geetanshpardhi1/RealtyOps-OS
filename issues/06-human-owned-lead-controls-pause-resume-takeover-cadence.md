# Issue #6: Human-Owned Lead Controls (pause/resume, takeover, cadence continuity)

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/6
Type: AFK
Blocked by: #4

## What to build
Create the Human-Owned Lead control slice so Brokerage Agent/admin users can pause/resume automation, manually take over with assist-only draft mode, and apply single-toggle Cadence Continuity Approval.

## Locked constraints
- Lead Contract fields used in this slice: `lead_id`, `status`, `owner_agent_id`, `qualification_state`, `confidence`, `escalation_flags`, `booking_control_mode`, `automation_paused`, `last_activity_at`.
- `qualification_state` values are canonical: `unqualified`, `partially_qualified`, `fully_qualified`.
- `status` is a separate lifecycle field and must not be inferred from `qualification_state`.
- `booking_control_mode` is canonical and must be one of: `autonomous`, `brokerage_controlled`.
- `automation_paused=true` pauses all autonomous actions (including outbound messaging, slot proposals, and booking attempts).
- Manual Brokerage Agent/admin operations remain allowed while `automation_paused=true`.

## Acceptance criteria
- [x] Brokerage Agent/admin can pause and resume lead automation.
- [x] Manual takeover enables assist-only draft mode with 72-hour checkpoint behavior.
- [x] Cadence Continuity Approval is a single control, not per-message approvals.
- [x] Pause semantics enforce full autonomous-action halt while preserving manual operations.

## Completion notes
- Added pause/resume endpoints:
  - `POST /leads/{lead_id}/automation/pause`
  - `POST /leads/{lead_id}/automation/resume`
- Added manual takeover endpoint with role guard (`brokerage_agent` or `admin`):
  - `POST /leads/{lead_id}/takeover`
  - Enforces `booking_control_mode=brokerage_controlled`, `assist_mode=draft_only`, `72h` checkpoint.
- Added single cadence continuity control endpoint:
  - `POST /leads/{lead_id}/cadence-continuity`
- Enforced pause semantics in autonomous outreach path:
  - `POST /outreach/first-touch` now returns `409 automation_paused` when paused.
- Added TDD coverage in `services/api/tests/test_human_owned_controls.py`.
