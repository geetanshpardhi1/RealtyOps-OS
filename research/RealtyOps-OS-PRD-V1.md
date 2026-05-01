## Problem Statement

Real-estate brokerage teams lose qualified demand because inbound leads are not handled with consistent speed and follow-through. Current operations are fragmented across lead sources, CRM, calendar, and messaging channels, creating manual bottlenecks, slow first response, inconsistent follow-up, and weak lead ownership accountability. The business impact is lower tour bookings and revenue leakage.

The team needs a production-credible V1 system that autonomously executes lead-to-tour workflows with guardrails, human-in-the-loop control, and measurable operational outcomes.

## Solution

Build RealtyOps OS V1 as a single-agent, execution-first Conversion Engine that:

- Ingests leads from website forms and Meta campaigns.
- Qualifies leads and routes ownership to a human brokerage agent.
- Executes outreach via WhatsApp first, with email fallback only on WhatsApp failure.
- Negotiates tour slots using shared calendar availability and books tours.
- Escalates to human ownership under strict handoff rules.
- Mirrors business artifacts into HubSpot while keeping workflow state in Firestore.
- Provides auditability, reliability controls, and operational metrics suitable for deployment and hackathon judging.

This V1 is implemented with Next.js (Vercel), Python/FastAPI services on Cloud Run, Google ADK, Firestore, Pub/Sub, Secret Manager, and Gemini on Vertex AI.

## User Stories

1. As a brokerage operations lead, I want all inbound website leads automatically captured, so that no new demand is lost at intake.
2. As a brokerage operations lead, I want all Meta leads automatically captured, so that paid campaign demand enters the same workflow.
3. As an AI workflow system, I want idempotent ingestion by external event key, so that duplicate webhook deliveries do not duplicate lead actions.
4. As an operations lead, I want each lead to have a canonical workflow record, so that status, ownership, and history are always clear.
5. As an AI agent, I want to qualify leads against required fields, so that downstream booking actions are policy-compliant.
6. As an AI agent, I want to escalate immediately when required qualification fields are missing, so that humans resolve risky ambiguity early.
7. As a brokerage manager, I want lead ownership assigned to a human agent after qualification/routing, so that accountability is explicit.
8. As an assigned owner agent, I want to see my lead queue and state transitions, so that I can prioritize action.
9. As an AI system, I want to send first-touch outreach on WhatsApp, so that response probability is maximized.
10. As an AI system, I want email fallback only when WhatsApp fails or is undelivered, so that channel policy remains consistent.
11. As an AI system, I want automatic follow-ups by default, so that lead decay is reduced without manual intervention.
12. As an owner agent, I want to pause or resume automation per lead, so that I can safely take manual control.
13. As an admin, I want override control over automation state, so that operational recovery is possible.
14. As an AI system, I want weekend follow-ups skipped, so that outreach aligns with business policy.
15. As an AI system, I want business-hour queueing in office timezone, so that outreach timing is operationally coherent.
16. As an AI system, I want to propose three slots per cycle, so that users get practical choice without message overload.
17. As an AI system, I want to limit negotiation to two cycles, so that unresolved scheduling gets human attention.
18. As an AI system, I want to negotiate only time slots and not price/rent, so that commercial risk is controlled.
19. As a lead, I want my booking treated as in-progress until calendar event creation succeeds, so that confirmations are trustworthy.
20. As a lead, I want immediate alternatives if my requested slot was just taken, so that booking can continue with low friction.
21. As operations, I want first-confirmed slot conflict rules, so that concurrent booking behavior is deterministic.
22. As operations, I want CRM task creation on escalation, so that handoff is system-of-record visible.
23. As operations, I want instant escalation alerts to a single ops inbox, so that human response starts quickly.
24. As an owner agent, I want forced booking allowed with mandatory reason capture, so that exceptional cases can be handled with auditability.
25. As compliance stakeholders, I want no AI hard commitments on pricing/inventory certainty, so that messaging remains safe.
26. As operations, I want stop-automation triggers on opt-out or abuse signals, so that consent and safety are respected.
27. As operations, I want human callback requests to force handoff, so that customer intent is honored.
28. As operations, I want auto-close after 14 days inactivity, so that stale pipeline is controlled.
29. As operations, I want auto-reopen on inbound reply after closure, so that renewed intent is not lost.
30. As CRM users, I want concise summarized notes in HubSpot, so that records remain readable and actionable.
31. As privacy stakeholders, I want full transcript retention internally for 90 days only, so that diagnostics and privacy are balanced.
32. As engineering, I want Firestore as workflow source of truth and HubSpot as mirror, so that orchestration remains deterministic.
33. As engineering, I want separated `crm-sync` processing, so that CRM outages do not block conversation flow.
34. As engineering, I want calendar booking with idempotency and conflict check, so that duplicate or invalid events are avoided.
35. As engineering, I want event-driven processing over Pub/Sub with DLQ, so that transient failures recover safely.
36. As engineering, I want structured logs and correlation IDs, so that incident debugging is fast.
37. As operations, I want daily visibility into first response time, follow-up completion, and tours per 100 leads, so that performance is measurable.
38. As founders, I want staging and production environments, so that demos are stable and production risk is reduced.
39. As engineering, I want automatic staging deploy and manual production promotion, so that release safety is maintained.
40. As judges/investors, I want reproducible architecture and reliability evidence, so that the system is credible beyond prototype.

## Implementation Decisions

- Product scope is frozen to website + Meta intake, WhatsApp-first outreach with email fallback, HubSpot + Google Calendar integrations, and ops inbox escalation.
- Backend runtime is Python/FastAPI with two Cloud Run services: `api` for ingestion/control and `worker` for asynchronous orchestration.
- Agent implementation uses Google ADK directly during development/testing and runtime execution.
- Workflow state source of truth is Firestore; HubSpot is a synchronized business-facing mirror.
- Event backbone uses Pub/Sub with separate domains for lead workflow and CRM sync, with dead-letter handling.
- Ingestion enforces mandatory idempotency before processing to prevent duplicate workflows.
- Qualification policy escalates immediately to human if required fields are missing.
- Ownership policy assigns a human `owner_agent` post-qualification/routing; only owner/admin can pause or resume automation.
- Slot negotiation policy uses three proposals per cycle, maximum two cycles, then escalation.
- Booking confirmation policy requires successful calendar event creation before customer confirmation is sent.
- Concurrency policy is first-confirmed-wins with automated alternatives for losing collisions.
- Outreach policy is WhatsApp primary, email fallback only on WhatsApp failure.
- Automation policy defaults follow-ups on, supports per-lead pause, skips weekends, and uses office-timezone business windows.
- Safety policy disallows AI hard commitments on pricing or inventory certainty.
- Retention policy stores CRM summaries externally and retains full internal transcripts for 90 days.
- Secrets policy is Secret Manager-only in deployed environments.
- Model policy is task-based split between lightweight routing/classification and stronger generation models.
- Release policy is staging auto-deploy from main and manual production promotion.
- Infrastructure is manually provisioned first, with later codification after stabilization.

Proposed deep modules (stable interfaces, high internal complexity):
- Lead Intake and Idempotency Gateway
- Qualification and Policy Engine
- Ownership and Routing Engine
- Outreach Orchestrator (channel policy + cadence)
- Slot Negotiation and Booking Coordinator
- Human Handoff and Escalation Manager
- CRM Mirror Sync Service
- State Machine and Audit Journal
- Observability and Reliability Control Plane

## Testing Decisions

- Good tests validate external behavior and contractual outcomes, not internal implementation details.
- Testing strategy uses a pyramid:
  - Unit tests for qualification rules, state transitions, routing decisions, policy guards.
  - Integration tests for adapters and external boundary behavior (messaging, CRM, calendar, secrets, queue consumers).
  - Scenario simulation tests for end-to-end multi-step reliability, including retries, conflicts, outages, and escalations.
- Priority test modules:
  - Ingestion idempotency and duplicate suppression
  - Qualification + escalation policy
  - Ownership permissions (owner/admin control semantics)
  - Slot negotiation cycle limits and fallback behavior
  - Booking confirmation gate and collision handling
  - CRM decoupled sync under outage conditions
  - Auto-close/reopen lifecycle behavior
  - Stop-automation safety triggers
- Quality evidence artifacts include scenario reports, latency/conversion simulation summaries, and failure recovery traces suitable for review.

## Out of Scope

- Multi-language support beyond English in V1.
- Price/rent negotiation and inventory certainty commitments by AI.
- Marketplace listing refactor concerns beyond V1 implementation.
- Fully generalized multi-agent architecture.
- Additional lead channels beyond website and Meta.
- Weekend follow-up execution.
- Advanced data warehouse analytics and BI pipelines.
- Immediate Terraform-first infrastructure as a hard requirement.

## Further Notes

- This PRD reflects locked discovery decisions from a structured grilling process and aligns to a challenge-ready V1 delivery strategy.
- Credit usage should prioritize model inference/evaluation and orchestration reliability while keeping frontend hosting on Vercel for delivery speed.
- The implementation should preserve a clear audit trail for every autonomous and human action to support operational trust and external judging narratives.
