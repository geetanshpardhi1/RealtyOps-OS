# Issue #3: Lead Intake + Idempotent Record Creation (Website + Meta)

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/3
Type: AFK
Blocked by: #2

## What to build
Implement a complete intake path for website and Meta leads that normalizes payloads, enforces idempotency, persists a canonical lead record, and emits a lead-created event for downstream orchestration.

## Acceptance criteria
- [x] Website and Meta intake requests create normalized lead records.
- [x] Duplicate deliveries are suppressed by idempotency keys.
- [x] A lead-created event is published for each unique lead intake.

## Completion notes
- Endpoints implemented:
  - `POST /intake/website`
  - `POST /intake/meta`
- Idempotency enforced by `source_event_id` (duplicate deliveries deduplicated).
- Canonical lead contract record is created for unique intake events.
- `lead.created` event emitted exactly once per unique intake.
- Covered by tests:
  - `services/api/tests/test_intake_website.py`
  - `services/api/tests/test_intake_meta.py`
  - `services/api/tests/test_intake_side_effects.py`
