# Issue #17: Scheduled Follow-up Runs on GCP (Cloud Scheduler -> Worker)

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/17
Type: AFK
Blocked by: #16
Status: Open

## What to build
Wire Cloud Scheduler to invoke the worker follow-up run on a fixed interval with authenticated requests so follow-up cadence executes automatically in staging/production without manual operator calls.

## Acceptance criteria
- [ ] Cloud Scheduler invokes worker follow-up run endpoint on a configured interval with OIDC-authenticated requests.
- [ ] Deployment configuration documents and provisions scheduler resources for staging.
- [ ] Operational checks verify scheduler-triggered runs produce persisted follow-up updates and events.

## Blocked by
- #16
