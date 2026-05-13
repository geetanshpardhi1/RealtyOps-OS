# Issue #13: Reliability Test Pyramid + Scenario Simulation Evidence

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/13
Type: AFK
Blocked by: #5, #6, #8, #10, #11, #12

## What to build
Create the verification slice with unit, integration, and scenario-simulation tests that demonstrate end-to-end reliability behavior and produce judge-ready evidence artifacts.

## Acceptance criteria
- [x] Critical domain behaviors are covered by unit and integration tests.
- [x] Scenario simulations validate edge cases and failure recovery paths.
- [x] Test outputs produce reproducible evidence for reliability claims.

## Completion notes
- Added scenario simulation suite:
  - `services/api/tests/test_scenario_simulation.py`
  - Scenarios cover:
    - WhatsApp failure -> email fallback -> booking retry-required path
    - CRM outage -> queued sync -> retry recovery path
- Added reproducible evidence generator:
  - `services/api/scripts/generate_reliability_evidence.py`
  - Produces judge-ready artifact:
    - `evidence/reliability-evidence.json`
  - Includes:
    - Test pyramid inventory (unit/integration/scenario file grouping)
    - Latest test run output and pass/fail state
    - Reliability claims and reproduction command
- Current reproducible run in evidence file shows:
  - `42 passed`
