# RealtyOps-OS

Monorepo scaffold for RealtyOps OS V1.

## Apps
- `apps/web`: Next.js dashboard shell (Vercel target)
- `services/api`: FastAPI intake/control service (Cloud Run target)
- `services/worker`: FastAPI worker/consumer service (Cloud Run target)

## Quick Start

### Web
```bash
cd apps/web
npm install
npm run dev
```

### API
```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Worker
```bash
cd services/worker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```
