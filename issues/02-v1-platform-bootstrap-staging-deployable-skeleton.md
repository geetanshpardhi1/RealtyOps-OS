# Issue #2: V1 Platform Bootstrap (staging deployable skeleton)

GitHub: https://github.com/geetanshpardhi1/RealtyOps-OS/issues/2
Type: AFK
Blocked by: None
Status: Completed

## What to build
Build a thin, end-to-end vertical slice that proves RealtyOps OS can deploy and run in staging with Clerk-authenticated dashboard access, Cloud Run API/worker services, Firestore connectivity, Pub/Sub wiring, and baseline health/status visibility.

## Acceptance criteria
- [x] Staging environment is deployable from CI and reachable for demo.
- [x] Dashboard auth works with role-based access boundaries.
- [x] API and worker health checks validate service readiness.

## Completion notes
- Dashboard auth + RBAC baseline added with Clerk:
  - `apps/web/app/dashboard/page.tsx` enforces role gates (`admin`, `brokerage_agent`, `operations`).
  - `apps/web/app/layout.tsx` wraps app in `ClerkProvider`.
- Service readiness endpoints available:
  - API: `GET /health`
  - Worker: `GET /health`
- CI staging deploy workflow added:
  - `.github/workflows/staging-deploy.yml`
  - Deploys API + Worker to Cloud Run on `main` (or manual dispatch).
- Deployment evidence verified on 2026-05-13:
  - API health: `https://realtyops-api-staging-3gpuwerbmq-el.a.run.app/health` => `{"status":"ok"...}`
  - Worker health: `https://realtyops-worker-staging-3gpuwerbmq-el.a.run.app/health` => `{"status":"ok"...}`
  - Web proxy health: `https://realtyops-os-web.vercel.app/api/health?target=api` => `{"ok":true,"status":"ok"}`
