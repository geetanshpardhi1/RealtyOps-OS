# Issue #15: Lead Contract Enrichment for Follow-up State

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/15
Type: AFK
Blocked by: #14
Status: Open

## What to build
Extend the canonical Lead Contract to persist follow-up state fields required for automated cadence execution and UI visibility, including due timestamps, attempt counters, latest outreach outcome, and continuity flags.

## Acceptance criteria
- [ ] Lead records persist follow-up state fields (`next_followup_at`, `followup_stage`, `last_outreach_at`, attempt metadata) in Firestore.
- [ ] Intake/qualification and existing lifecycle APIs preserve backward compatibility while writing/reading the new fields.
- [ ] Dashboard Lead detail renders the persisted follow-up state consistently with API responses.

## Blocked by
- #14
