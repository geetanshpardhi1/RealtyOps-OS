# Issue #7: Slot Negotiation + Concurrency Handling (3 slots x 2 cycles)

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/7
Type: AFK
Blocked by: #5

## What to build
Implement slot negotiation that proposes three slots per cycle, caps at two cycles, and deterministically handles concurrent slot contention with first-confirmed-wins and automatic alternative proposals.

## Acceptance criteria
- [x] Slot proposals follow 3-per-cycle behavior with max two cycles.
- [x] Concurrent slot collisions are handled with first-confirmed-wins semantics.
- [x] Losing collision path sends immediate alternatives without dead-ending the flow.

## Completion notes
- Added `POST /leads/{lead_id}/slot-negotiation/propose`:
  - Exactly 3 candidate slots per cycle.
  - Hard cap at 2 cycles (`cycle > 2` returns `409 max_cycles_exceeded`).
- Added `POST /leads/{lead_id}/slot-negotiation/confirm`:
  - First-confirmed-wins on slot contention.
  - Collision response returns winner lead and immediate alternative slots.
- Added slot negotiation audit events:
  - `slot.proposed`, `slot.confirmed`, `slot.collision`.
- Added TDD coverage in `services/api/tests/test_slot_negotiation.py`.
