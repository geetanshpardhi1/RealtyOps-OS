# First Run Demo

## 1) Prerequisites
- `python3`, `node`, `npm`
- Clerk app keys
- Optional: GCP project for Cloud Run staging deploy

## 2) Environment
Populate `.env.example` values as needed.

Web required for Clerk:
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`

## 3) Run API
```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 4) Run Worker
```bash
cd services/worker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## 5) Run Web
```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`, sign in with Clerk, and go to `/dashboard`.

## 6) Demo Validation
- API health: `curl http://localhost:8000/health`
- Worker health: `curl http://localhost:8001/health`
- Intake smoke:
```bash
curl -X POST http://localhost:8000/intake/website \
  -H 'content-type: application/json' \
  -d '{
    "source_event_id":"evt_demo_001",
    "contact":{"phone":"+919999999999","email":"demo@example.com","first_name":"Demo"},
    "preferences":{"preferred_locality":"Powai","budget_range":"80L-1Cr","move_in_timeline":"30_days"}
  }'
```

## 7) Reliability Evidence
```bash
cd services/api
.venv/bin/python -m pytest -q
.venv/bin/python scripts/generate_reliability_evidence.py
```
Artifact: `evidence/reliability-evidence.json`

## 8) GCP Staging Bootstrap (One-Time)
```bash
cd /Users/geetansh/Developer/RealtyOps-OS
./scripts/gcp_bootstrap.sh
```

Optional overrides:
```bash
PROJECT_ID=realtyops-os-staging \
REGION=asia-south1 \
REPO=geetanshpardhi1/RealtyOps-OS \
./scripts/gcp_bootstrap.sh
```
