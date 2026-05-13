# Issue #12: Observability + KPI Dashboard Metrics + Alerting

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/12
Type: AFK
Blocked by: #3

## What to build
Deliver an end-to-end observability slice with structured logs, correlation identifiers, business KPIs, and alerting so operations can monitor lead flow reliability and conversion performance daily.

## Acceptance criteria
- [x] Structured logs include lead and event correlation identifiers.
- [x] Daily KPIs include first response time, follow-up completion, and tours per 100 leads.
- [x] Alerting covers critical failure patterns (webhooks, DLQ growth, booking failures).

## Completion notes
- Added structured-correlation observability endpoint:
  - `POST /observability/correlation-log`
  - Captures `lead_id`, generated `event_id`, and `correlation_id` (`X-Correlation-ID` support).
  - Emits structured log entry + event payload with correlation fields.
- Added daily KPI dashboard endpoint:
  - `GET /observability/kpi/daily`
  - Computes:
    - `first_response_time_minutes`
    - `follow_up_completion_rate`
    - `tours_per_100_leads`
- Added alert evaluation endpoint:
  - `GET /observability/alerts/evaluate`
  - Detects critical patterns:
    - webhook failures
    - DLQ growth
    - booking failures
- Added TDD coverage in `services/api/tests/test_observability_kpi_alerting.py`.
