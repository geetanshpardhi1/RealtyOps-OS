# RealtyOps OS V1 Implementation Blueprint

## 1. Objective
Build and deploy a production-credible V1 single-agent system that converts inbound real-estate leads into scheduled tours with hybrid human oversight.

Primary business outcome: increase booked tours by reducing response delay and follow-up drop-off.

## 2. Locked V1 Scope

### 2.1 Inbound Channels
- Website form leads
- Meta leads (ads/campaign webhooks)

### 2.2 Outreach Channels
- Primary: WhatsApp (Twilio WhatsApp)
- Fallback: Email only if WhatsApp fails/undelivered

### 2.3 Core Integrations
- HubSpot (CRM mirror + tasks)
- Google Calendar (tour booking)

### 2.4 Internal Escalation Channel
- Single operations inbox email

### 2.5 Language, Time, and Cadence
- Language: English only (V1)
- Business window: office timezone
- Weekend behavior: skip Saturday and Sunday follow-ups

## 3. High-Level Architecture

## 3.1 Frontend
- Next.js dashboard on Vercel
- Clerk authentication
- Roles: admin, assigned owner-agent, viewer

## 3.2 Backend Services (GCP)
- Cloud Run service 1: `api`
  - Intake endpoints (website/meta)
  - Admin endpoints for dashboard actions
- Cloud Run service 2: `worker`
  - Pub/Sub consumers
  - ADK agent execution and tool-calling

## 3.3 Data and Messaging
- Firestore: workflow source of truth
- Pub/Sub: async event bus + retries + DLQ
- Separate topic/consumer for CRM sync (`crm-sync`)

## 3.4 AI/Agent Layer
- Google ADK used in implementation/testing and runtime orchestration
- Task-based model split
  - Lightweight model: classification/routing/extraction
  - Stronger model: nuanced response generation

## 3.5 Security and Ops
- Secret Manager only for deployed secrets
- Cloud Logging + Cloud Monitoring
- Custom business metrics + alert policies from day 1

## 4. End-to-End Lead Flow

1. Lead arrives from website or Meta webhook.
2. `api` validates payload, enforces idempotency key gate.
3. `api` writes minimal lead record to Firestore (`status=new`, `owner_agent_id=null`).
4. `api` publishes `lead.created` event to Pub/Sub.
5. `worker` consumes event and runs ADK qualification step.
6. If required info is missing, escalate to human immediately (`needs_human`) and create CRM task + ops email.
7. If qualified enough, run assignment logic and set `owner_agent_id`.
8. Send first outreach via WhatsApp.
9. If WhatsApp undelivered/fails, fallback to email.
10. If lead engages, negotiate slots (3 slots per cycle, max 2 cycles).
11. On slot acceptance, attempt calendar booking with conflict check + idempotency.
12. If conflict, send apology + next closest slots.
13. Booking is confirmed only after calendar event creation succeeds.
14. Send confirmation acknowledgment only after booking success.
15. Publish CRM mirror updates through `crm-sync` topic/consumer.
16. Run automated follow-ups by default when needed; owner/admin can pause per lead.
17. Auto-close lead after 14 days of inactivity.
18. Auto-reopen if any new inbound reply arrives.

## 5. Human-in-the-Loop and Ownership Model

- AI is execution layer, not accountable owner.
- Human owner is the accountable broker/agent assigned to lead.
- Assignment occurs after qualification/routing.
- Only assigned owner + admin can pause/resume automation and execute sensitive manual controls.
- Owner can force-book with mandatory reason note in audit trail.

## 6. State Machine (V1)

Core statuses:
- `new`
- `qualifying`
- `assigned`
- `outreach_sent`
- `negotiating`
- `pending_confirmation`
- `tour_scheduled`
- `needs_human`
- `paused`
- `closed`

Transition highlights:
- `new -> qualifying` after event ingestion
- `qualifying -> needs_human` if required fields missing
- `qualifying -> assigned` when qualified + routing complete
- `assigned -> outreach_sent` after first send attempt
- `outreach_sent -> negotiating` on engagement
- `negotiating -> pending_confirmation` on verbal slot acceptance
- `pending_confirmation -> tour_scheduled` only on calendar success
- `* -> paused` by owner/admin toggle
- `closed -> assigned/negotiating` on inbound reactivation

## 7. ADK Toolset (Small Fixed Set)

- `qualify_lead`
- `assign_owner`
- `send_whatsapp`
- `send_email_fallback`
- `get_available_slots`
- `create_calendar_booking`
- `escalate_to_human`
- `enqueue_followup`
- `sync_crm_record`

Notes:
- Keep tool schemas deterministic.
- Enforce guardrails against pricing/inventory commitments.

## 8. Data Model (Firestore)

## 8.1 Collections
- `leads/{lead_id}`
- `lead_events/{event_id}`
- `messages/{message_id}`
- `tasks/{task_id}`
- `audit_logs/{audit_id}`

## 8.2 Lead Document Fields (minimum)
- `lead_id`
- `source` (`website` | `meta`)
- `source_event_id` (idempotency key)
- `status`
- `owner_agent_id` (nullable)
- `qualification` object
- `contact` object
- `preferred_locality`
- `budget_range`
- `move_in_timeline`
- `automation_paused` (bool)
- `last_activity_at`
- `created_at`, `updated_at`

## 8.3 Audit Requirements
Track every critical action with:
- actor (`system` | `owner` | `admin`)
- action
- reason (mandatory for force-book/manual override)
- timestamp

## 9. Event Contracts (Pub/Sub)

Topics:
- `lead-events`
- `followup-events`
- `crm-sync`
- `dead-letter`

Event examples:
- `lead.created`
- `lead.qualified`
- `lead.escalated`
- `outreach.sent`
- `slot.proposed`
- `booking.pending`
- `booking.confirmed`
- `lead.closed`
- `lead.reopened`

Contract rules:
- Include `event_id`, `lead_id`, `event_type`, `occurred_at`, `idempotency_key`.
- Consumers must be idempotent.

## 10. Booking and Concurrency Rules

- Single shared Tours Calendar.
- First confirmed booking wins.
- If second lead collides on same slot:
  - immediate unavailability acknowledgment
  - offer next 2-3 nearest slots
- Max slot negotiation: 3 slots per cycle, 2 cycles total.

## 11. Follow-Up and Stop Rules

Default:
- Automation follow-ups enabled.
- Pause/resume allowed for owner/admin.

Stop automation triggers:
- not interested
- stop/do-not-contact
- abusive content
- asks for human callback

Escalate immediately for:
- missing required qualification fields
- complex property/legal/negotiation questions

## 12. Reliability, Error Handling, and SRE Baseline

## 12.1 Retries
- Exponential backoff for transient external failures.
- DLQ after max attempts.

## 12.2 Degraded Behavior
- HubSpot down: continue conversation, queue CRM sync, alert ops.
- Calendar failure: silent short retry, then apologize and re-propose slots.

## 12.3 Observability
- Structured logs with correlation IDs (`lead_id`, `event_id`).
- Custom metrics:
  - first response latency
  - follow-up completion
  - tours per 100 leads
  - escalation rate
  - booking failure rate
- Alerts:
  - webhook failure spikes
  - DLQ growth
  - booking API failures

## 13. Security and Privacy

- Secrets only in Secret Manager.
- Least-privilege IAM per service account.
- CRM stores summary notes only.
- Full transcript retained internally for 90 days, then delete or redact.

## 14. Testing Strategy

Test pyramid:
- Unit tests: qualification logic, routing, state transitions, guardrails
- Integration tests: HubSpot, Calendar, Twilio adapters with mocks/sandboxes
- Scenario simulation harness:
  - no-response journeys
  - conflicting slots
  - duplicate leads
  - API outage cases
  - escalation trigger cases

Evidence output for judging:
- pass/fail report
- latency/conversion simulation table
- failure recovery logs

## 15. Deployment Strategy

Environments:
- `staging`
- `production`

CI/CD:
- GitHub Actions from start
- `main` auto deploys to staging
- production deploy is manual promote/approval

Frontend deployment:
- Vercel

Backend deployment:
- Cloud Run `api`
- Cloud Run `worker`

## 16. Budget Control Plan ($500 Credit)

Target split:
- Vertex AI usage: 40-45%
- Cloud Run compute: 20-25%
- Firestore + Pub/Sub: 15-20%
- Logging/Monitoring: 5-10%
- Buffer: 10-15%

Guardrails:
- Billing alerts at 50%, 80%, 100%
- per-service dashboard for daily spend check
- enforce model selection policy by task type

## 17. Build Plan (0 to 100)

### Phase 0: Foundation (Day 1-2)
1. Create GCP project, billing, budgets, alerts.
2. Enable APIs: Cloud Run, Firestore, Pub/Sub, Secret Manager, Vertex AI, Logging/Monitoring.
3. Create service accounts and IAM roles.
4. Set up Secret Manager entries.
5. Configure Firestore and Pub/Sub topics/subscriptions + DLQ.

### Phase 1: Skeleton Services (Day 3-5)
1. Scaffold `api` and `worker` FastAPI services.
2. Add health endpoints and structured logging.
3. Add GitHub Actions for staging deploy.
4. Deploy both services to Cloud Run staging.

### Phase 2: Ingestion + State Core (Day 6-9)
1. Build website/meta intake endpoints.
2. Add idempotency gate and minimal lead write.
3. Publish `lead.created` events.
4. Implement base state machine in Firestore.

### Phase 3: ADK Agent Core (Day 10-15)
1. Implement ADK tools (small fixed set).
2. Implement qualification and assignment flow.
3. Implement outreach send with WhatsApp primary + email fallback.
4. Add escalation triggers and ops inbox alerting.

### Phase 4: Booking Engine (Day 16-20)
1. Implement slot fetch and proposal engine (3 slots per cycle).
2. Add max 2-cycle logic.
3. Implement calendar booking with idempotency + conflict checks.
4. Finalize `pending_confirmation -> tour_scheduled` confirmation logic.

### Phase 5: Follow-ups + CRM Mirror (Day 21-24)
1. Implement follow-up scheduling with business-window and weekend skip rules.
2. Implement pause/resume controls (owner/admin only).
3. Build separate `crm-sync` consumer.
4. Add auto-close (14 days) and auto-reopen on inbound reply.

### Phase 6: Dashboard + Manual Controls (Day 25-28)
1. Build Vercel dashboard views for lead states.
2. Add owner assignment visibility and audit timeline.
3. Add manual override controls including force-book reason capture.
4. Integrate Clerk roles and access control.

### Phase 7: Reliability + Testing (Day 29-33)
1. Unit + integration tests across critical flows.
2. Scenario simulation harness.
3. Add failure injection tests for HubSpot/Calendar outages.
4. Tune retries, DLQ handling, and alert thresholds.

### Phase 8: Submission Hardening (Day 34-36)
1. Prepare architecture diagram and implementation narrative.
2. Capture KPI evidence tables and log screenshots.
3. Record end-to-end demo.
4. Production readiness checklist and final deploy promote.

## 18. Definition of Done (V1)

- Intake to scheduled tour flow works end-to-end on staging and production.
- Human handoff and manual controls are operational.
- Observability and alerting are active.
- Test suite + scenario simulation results are available.
- Submission artifacts are complete and reproducible.
