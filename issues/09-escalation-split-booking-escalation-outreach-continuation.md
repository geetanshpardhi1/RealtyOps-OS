# Issue #9: Escalation Split: Booking Escalation + Outreach Continuation

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/9
Type: AFK
Blocked by: #6, #8

## What to build
Deliver the escalation split where low/borderline confidence or high-risk conditions escalate booking control to Brokerage Agent while Outreach Continuation can still run on defined cadence unless paused.

## Acceptance criteria
- [x] Booking Escalation triggers on defined risk/confidence rules.
- [x] Outreach Continuation remains active at T+24h and T+72h unless paused.
- [x] No autonomous booking attempts occur while escalated conditions are active.

## Completion notes
- Added `POST /leads/{lead_id}/escalation/evaluate`:
  - Escalates booking when confidence is low/borderline or risk flags are present.
  - Sets `booking_escalated`, `booking_escalation_reasons`, and `booking_control_mode=brokerage_controlled`.
- Added `POST /leads/{lead_id}/outreach/continuation/plan`:
  - Keeps outreach continuation active on T+24h and T+72h while escalated.
  - Disables continuation when `automation_paused=true`.
- Updated autonomous booking path:
  - `POST /leads/{lead_id}/booking/attempt` now blocks with `409 booking_escalated_human_control_required` when escalation is active.
- Added audit events:
  - `lead.booking_escalation_evaluated`
  - `outreach.continuation_planned`
- Added TDD coverage in `services/api/tests/test_escalation_split.py`.
