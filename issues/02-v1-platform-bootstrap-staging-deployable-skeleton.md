# Issue #2: V1 Platform Bootstrap (staging deployable skeleton)

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/2
Type: AFK
Blocked by: None

## What to build
Build a thin, end-to-end vertical slice that proves RealtyOps OS can deploy and run in staging with Clerk-authenticated dashboard access, Cloud Run API/worker services, Firestore connectivity, Pub/Sub wiring, and baseline health/status visibility.

## Acceptance criteria
- [ ] Staging environment is deployable from CI and reachable for demo.
- [x] Dashboard auth works with role-based access boundaries.
- [x] API and worker health checks validate service readiness.

## Completion notes
- Dashboard auth + RBAC baseline added with Clerk:
  - `apps/web/middleware.ts` protects `/dashboard`.
  - `apps/web/app/dashboard/page.tsx` enforces role gates (`admin`, `brokerage_agent`, `operations`).
  - `apps/web/app/layout.tsx` wraps app in `ClerkProvider`.
- Service readiness endpoints available:
  - API: `GET /health`
  - Worker: `GET /health`
- CI staging deploy workflow added:
  - `.github/workflows/staging-deploy.yml`
  - Deploys API + Worker to Cloud Run on `main` (or manual dispatch) when required GCP secrets are set.
- First-run demo runbook and script added:
  - `docs/FIRST_RUN_DEMO.md`
  - `scripts/demo_first_run.sh`

## Remaining external step
- Configure GitHub secrets (`GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`, `GCP_REGION`, `PUBSUB_LEAD_EVENTS_TOPIC`, `FIRESTORE_DATABASE`) and trigger `Staging Deploy` once to satisfy the final staging reachability checkbox.
