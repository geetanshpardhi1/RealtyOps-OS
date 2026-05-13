# Issue #5: WhatsApp-First Outreach with Email Fallback

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/5
Type: AFK
Blocked by: #4

## What to build
Implement outreach orchestration that sends first contact through WhatsApp and automatically falls back to email only when WhatsApp delivery fails, while preserving auditability and policy constraints.

## Acceptance criteria
- [x] First-touch outreach is attempted via WhatsApp for eligible leads.
- [x] Email fallback triggers only on WhatsApp failure/undelivered outcomes.
- [x] Outreach events are logged with channel and delivery outcome.

## Completion notes
- Added `POST /outreach/first-touch` in API with eligibility gate (`partially_qualified` or `fully_qualified`).
- Implemented WhatsApp-first attempt and strict email fallback only for `failed`/`undelivered`.
- Added audit event emission (`outreach.attempted`) with `channel` and `delivery_outcome` for each attempt.
- Added TDD coverage in `services/api/tests/test_outreach_fallback.py`.
