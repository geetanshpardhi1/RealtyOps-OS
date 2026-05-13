# Issue #8: Autonomous Booking Gate + Calendar Confirmation Path

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/8
Type: AFK
Blocked by: #7

## What to build
Implement booking confirmation through the Autonomous Booking Gate: Fully Qualified status, confidence >= 0.80, no active escalation flags, and successful calendar event creation before confirming tour booking.

## Acceptance criteria
- [x] Booking attempts enforce the full Autonomous Booking Gate.
- [x] Tour is confirmed only after calendar write success.
- [x] Failed/conflicting booking attempts recover through retry/fallback behavior.

## Completion notes
- Added `POST /leads/{lead_id}/booking/attempt` with autonomous gate enforcement:
  - `qualification_state == fully_qualified`
  - `confidence >= 0.80`
  - no active `escalation_flags`
- Implemented calendar-confirmed booking semantics:
  - booking moves to `in_progress` first
  - confirmation only after calendar writer returns success + event id
  - then lead transitions to `status=booked`, `booking_status=confirmed`
- Implemented retry/fallback path:
  - on failure/conflict, retries with first fallback slot
  - if still unsuccessful, returns `retry_required` plus recommended slots
- Added booking lifecycle audit events:
  - `booking.in_progress`, `booking.confirmed`, `booking.failed`
- Added TDD coverage in `services/api/tests/test_autonomous_booking_gate.py`.
