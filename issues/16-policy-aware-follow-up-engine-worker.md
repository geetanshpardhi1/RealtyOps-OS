# Issue #16: Policy-aware Follow-up Engine in Worker (Manual Trigger + Persisted Outcomes)

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/16
Type: AFK
Blocked by: #15
Status: Open

## What to build
Implement a policy-aware Follow-up Engine in the worker that processes due Leads, executes WhatsApp-first outreach with email fallback, records delivery outcomes, and respects pause/escalation/weekend rules while keeping lead state and event logs auditable.

## Acceptance criteria
- [ ] Worker exposes a run endpoint/job that processes due follow-ups and updates Lead follow-up fields deterministically.
- [ ] Channel execution follows WhatsApp-first and email fallback semantics with persisted outcome events.
- [ ] Policy guards are enforced (`automation_paused`, Booking Escalation controls, weekend skip), with tests for allowed and blocked paths.

## Blocked by
- #15
