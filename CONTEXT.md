# RealtyOps OS

A conversion-operations context for real-estate brokerages that turns inbound demand into scheduled property tours through AI execution with human accountability.

## Language

**Lead**:
A prospective buyer or renter entering the brokerage funnel from an intake channel.
_Avoid_: prospect record, inquiry row

**Brokerage Agent**:
The human salesperson accountable for the lead outcome and manual intervention decisions.
_Avoid_: Owner agent, assigned owner, human-in-loop agent

**Partially Qualified**:
A lead state where information is sufficient for human ownership assignment but not sufficient for autonomous booking.
_Avoid_: soft-qualified, half-qualified

**Fully Qualified**:
A lead state where required qualification fields are complete and valid for autonomous booking flow.
_Avoid_: qualified enough

**Assignment Gate**:
The rule that a lead can be assigned to a Brokerage Agent only after reaching Partially Qualified state.
_Avoid_: pre-qualification assignment

**Booking Escalation**:
The rule that low-confidence or borderline leads are routed immediately to human control for booking decisions.
_Avoid_: autonomous booking retry loops on low confidence

**Outreach Continuation**:
The rule that follow-up outreach cadence may continue after booking escalation unless manually paused.
_Avoid_: assuming escalation means all messaging stops

**Cadence Continuity Approval**:
A single control in human-owned mode that enables or disables scheduled outbound follow-up cadence without per-message approvals.
_Avoid_: per-cadence-message approvals

**Human-Owned Lead**:
A lead accountability mode where a Brokerage Agent owns decisions and override rights while AI may still execute allowed operational steps (including slot discovery/proposal) under policy guardrails.
_Avoid_: assuming only humans can send slots or links

**Autonomous Booking Gate**:
The rule that AI may auto-confirm booking only when the lead is Fully Qualified, confidence is at least 0.80, no active escalation flags exist, and calendar event creation succeeds.
_Avoid_: confirming bookings on intent alone

**Identity Merge Rule**:
The policy that exact phone match auto-merges leads, exact email match auto-merges only when phone is missing, and phone-email conflicts require human review.
_Avoid_: blind auto-merge on conflicting identity signals

**Lead Contract**:
The minimal canonical lead record fields that all workflows must share for consistent state transitions and ownership semantics.
_Avoid_: per-module ad hoc lead shapes

## Relationships

- A **Lead** is accountable to exactly one **Brokerage Agent** once assigned
- A **Brokerage Agent** can own many **Leads**
- A **Lead** can move from **Partially Qualified** to **Fully Qualified**
- **Assignment Gate** occurs at **Partially Qualified** and not before
- **Booking Escalation** can occur while **Outreach Continuation** remains active
- **Cadence Continuity Approval** is controlled only by assigned **Brokerage Agent** or admin
- A **Human-Owned Lead** can still receive AI-operated slot proposals and follow-ups when policy allows
- **Autonomous Booking Gate** must pass before booking confirmation is sent
- **Identity Merge Rule** determines whether inbound records are auto-merged or queued for human review
- **Lead Contract** is the shared baseline for intake, qualification, outreach, booking, escalation, and reporting

## Example dialogue

> **Dev:** "Can this lead be auto-booked now?"
> **Domain expert:** "No, it is only **Partially Qualified**; assign a **Brokerage Agent** first."

## Flagged ambiguities

- "owner agent" and "human in the loop" were used interchangeably with **Brokerage Agent** — resolved: use **Brokerage Agent** as canonical term.
- "qualified enough" conflicted with strict qualification language — resolved into **Partially Qualified** and **Fully Qualified**.
- "escalation" was ambiguous between booking control and messaging flow — resolved into **Booking Escalation** plus **Outreach Continuation**.
- "human-owned" was confused with manual-only execution — resolved: it defines accountability and override authority, not channel execution exclusivity.
- "booking confirmation" was ambiguous between accepted intent and confirmed schedule — resolved via **Autonomous Booking Gate**.
- "lead schema" risked fragmenting across parallel tracks — resolved by canonical **Lead Contract**.

## Technical Baseline (V1)

- Frontend: Next.js (`apps/web`) with Clerk authentication and role-gated dashboard
- API service: FastAPI (`services/api`) deployed on Cloud Run
- Worker service: FastAPI (`services/worker`) deployed on Cloud Run
- Primary data store: Firestore (`(default)` database)
- Event bus: Pub/Sub topic `lead-events`
- CI/CD: GitHub Actions staging deploy via Workload Identity Federation (OIDC), no static GCP JSON keys
- Frontend hosting target: Vercel
- Backend hosting target: Google Cloud Run

## Deployment Context (As of 2026-05-13)

- Active GCP project id: `steel-aileron-475104-a5`
- Active GCP project display name: `RealtyOps OS`
- Cloud Run region: `asia-south1`
- Runtime service account pattern: dedicated deployer SA + dedicated runtime SA
- Staging API URL: `https://realtyops-api-staging-3gpuwerbmq-el.a.run.app`
- Staging Worker URL: `https://realtyops-worker-staging-3gpuwerbmq-el.a.run.app`
- Staging workflow source: `.github/workflows/staging-deploy.yml`
- Vercel production alias: `https://realtyops-os-web.vercel.app`
- Latest Vercel production deployment (at update time): `https://realtyops-os-ou4yswq0h-geetanshpardhi1s-projects.vercel.app`

## Operational Guardrails (Confirmed)

- Outreach channel order: WhatsApp first, email fallback if WhatsApp fails
- Booking is confirmed only after calendar event creation succeeds
- Low-confidence or borderline leads escalate immediately for booking decisions
- Outreach cadence may continue during booking escalation unless paused
- Cadence approval is a single continuity control, not per-message approval

## Project Scope and Goal (V1)

- Build a production-oriented lead-operations OS for brokerages where AI handles intake, qualification, outreach cadence, slot negotiation, and booking operations with explicit human accountability controls.
- Target outcome: reliable first-run demo + deployable staging system with observable health, deterministic lead-state transitions, and audit-friendly behavior.
- Current delivery status: backend staging is live on GCP Cloud Run; frontend is live on Vercel with Clerk auth and role-gated dashboard.

## Repo Map (What Lives Where)

- `apps/web`: Next.js UI + Clerk auth + role-gated `/dashboard`
- `services/api`: FastAPI orchestration service (intake, qualification, outreach, booking, escalation, lifecycle, observability APIs)
- `services/worker`: FastAPI worker service for async/background service role
- `services/api/tests`: test pyramid coverage for V1 behavior
- `evidence/reliability-evidence.json`: generated reliability artifact
- `issues/`: local mirror of implementation issues
- `.github/workflows/staging-deploy.yml`: Cloud Run staging deploy workflow
- `scripts/gcp_bootstrap.sh`: one-shot GCP + GitHub secret bootstrap script
- `docs/FIRST_RUN_DEMO.md`: local/staging runbook

## Implemented Capabilities (Completed)

- Intake:
- Website intake endpoint with idempotency by `source_event_id`
- Dedup behavior validated (`deduplicated=false` then `true` on replay)
- Qualification and assignment:
- Lead qualification states include Partially Qualified and Fully Qualified semantics
- Assignment gate at Partially Qualified before ownership assignment
- Outreach:
- WhatsApp-first flow with email fallback strategy
- Automation pause/manual control options on lead
- Slot negotiation and booking:
- Shared tour calendar model
- Multi-cycle slot proposal logic and conflict handling
- Booking confirmation only after calendar event creation success
- Escalation and human controls:
- Immediate booking escalation for low-confidence/borderline cases
- Outreach continuation allowed during booking escalation unless paused
- Human-owned control model with takeover and cadence continuity switch
- Lifecycle and CRM:
- Auto-close window set to 14 days inactivity
- Auto-reopen allowed on inbound activity
- CRM sync handling with retry/queue + outage-aware behavior
- Observability:
- Health endpoints for API and worker
- KPI/alerting and reliability evidence path in repo

## Deployment and Infra State (Verified)

- GCP project:
- `project_id`: `steel-aileron-475104-a5`
- `project_name`: `RealtyOps OS`
- `region`: `asia-south1`
- Cloud Run services:
- API: `https://realtyops-api-staging-3gpuwerbmq-el.a.run.app`
- Worker: `https://realtyops-worker-staging-3gpuwerbmq-el.a.run.app`
- Service accounts:
- Deployer: `github-deployer@steel-aileron-475104-a5.iam.gserviceaccount.com`
- Runtime: `realtyops-runtime@steel-aileron-475104-a5.iam.gserviceaccount.com`
- WIF/OIDC deploy path:
- GitHub Actions auth uses Workload Identity Federation (no static JSON key)
- Vercel frontend project:
- `realtyops-os-web` under scope `geetanshpardhi1s-projects`
- Production deploy URL (latest): `https://realtyops-os-ou4yswq0h-geetanshpardhi1s-projects.vercel.app`
- Production alias: `https://realtyops-os-web.vercel.app`

## Current Frontend Runtime Notes

- Framework configuration for Vercel is pinned via `apps/web/vercel.json` with `"framework": "nextjs"` to avoid route-level `404` behavior seen under `Other` preset.
- Clerk middleware file remains removed due edge/runtime incompatibility in this stack combination.
- Home and dashboard use client-side Clerk hooks (`useUser`) for auth state and role rendering.
- Dashboard role is currently read from `user.publicMetadata.role` on client.
- Dashboard now reads:
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_WORKER_BASE_URL`
- Dashboard health checks are routed via same-origin Next route `GET /api/health` to avoid browser CORS issues and to keep endpoint wiring centralized.

## Known Constraints / Risks

- Vercel route-level `404` issue has been resolved by explicit Next.js framework config + fresh deployment.
- Clerk server `auth()` path was removed from pages to avoid runtime failures without middleware; this is a pragmatic stability choice, not final security hardening.
- Authorization on dashboard is UI-level role gating; sensitive backend actions must still be protected server-side in API services.
- Next.js `14.2.5` and some web dependencies are deprecated/vulnerable per install warnings; upgrade hardening is pending.
- Clerk packages in use include deprecated modules (`@clerk/clerk-react`, `@clerk/types`) via transitive setup; migration cleanup pending.

## What Is Done vs Pending

- Done:
- Core V1 backend behavior and tests implemented
- Staging backend deployed and reachable (`/health` ok)
- Frontend deployed with env wiring to staging backends
- Frontend production alias now serves app successfully (`/` and `/dashboard` return `200`)
- Frontend health proxy endpoint returns `ok` for API and worker targets
- Live intake idempotency demo validated on staging:
- `source_event_id=evt_demo_live_001`
- first call: `deduplicated=false`, `lead_id=lead_7bd3d469c293`
- second same payload: `deduplicated=true`, same `lead_id`
- Context, runbook, and bootstrap automation created
- Pending (next practical steps):
- Reintroduce robust server-side auth enforcement path (middleware or equivalent) after Clerk/Vercel compatibility upgrade
- Security/maintenance pass: dependency upgrades (Next.js + Clerk migration)
- End-to-end UX validation: login -> dashboard -> health statuses -> intake trigger demo

## Latest Demo Verification (2026-05-13)

- Web:
- `GET /` on `https://realtyops-os-web.vercel.app` => `200`
- `GET /dashboard` on `https://realtyops-os-web.vercel.app` => `200`
- `GET /api/health?target=api` => `{"ok":true,"status":"ok"}`
- `GET /api/health?target=worker` => `{"ok":true,"status":"ok"}`
- Backend:
- `GET https://realtyops-api-staging-3gpuwerbmq-el.a.run.app/health` => `{"status":"ok","service":"api","adapter_mode":"gcp"}`
- `GET https://realtyops-worker-staging-3gpuwerbmq-el.a.run.app/health` => `{"status":"ok","service":"worker"}`

## Handoff Checklist for Next Agent/Developer

- Read this file + `docs/FIRST_RUN_DEMO.md` first.
- Verify backend health endpoints:
- API: `/health`
- Worker: `/health`
- Confirm Vercel project env vars exist:
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_WORKER_BASE_URL`
- Confirm `apps/web/vercel.json` remains present with Next.js framework config in future refactors.
- Check current GitHub Actions runs for `staging-deploy.yml`.
- If tackling frontend auth hardening, treat Clerk+Vercel edge compatibility as first-class constraint.
