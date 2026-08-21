# TrackChain Production Deployment Guide (tc.v1)

This guide documents the multi-tier deployment configuration for the TrackChain railway track monitoring platform.

---

## 1. System Architecture

```
[ Edge Fleet (RPi5 / Jetson) ] 
               │  (4G/5G HTTPS TLS 1.3)
               ▼
[ Ingestion Gateway / FastAPI Backend ] ──► [ TimescaleDB / Postgres ]
               ▲                             [ MinIO / AWS S3 ]
               │  (REST API + SSE Stream)
[ Next.js Mission Control (Vercel) ]
```

---

## 2. Frontend Deployment (Next.js on Vercel)

### Step 1: Connect GitHub Repository
1. Log into your [Vercel Dashboard](https://vercel.com).
2. Click **"Add New..."** → **"Project"** and select `Mayank8159/TrackChain`.
3. Set **Framework Preset** to `Next.js`.
4. Set **Root Directory** to `./` (monorepo root) or `./app`.

### Step 2: Environment Variables
Configure the following in **Project Settings** → **Environment Variables**:

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Public HTTPS URL of the live FastAPI backend | `https://trackchain-backend.onrender.com` |
| `NEXT_PUBLIC_DEMO_DEFAULT` | Set default mode on first load (`DEMO` or `REAL`) | `DEMO` |

### Step 3: Deploy
* Trigger deployment on the `main` branch.
* Production URL: `https://trackchain.vercel.app`.

---

## 3. Backend Deployment (FastAPI on Railway / Docker / Render)

### Option A: Railway (Container Deployment)
1. In Railway, create a new project from `Mayank8159/TrackChain`.
2. Set root directory to `backend`.
3. Set Build Command: `pip install -r requirements.txt`.
4. Set Start Command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`.

### Option B: Docker Compose (Dedicated VM / On-Premise Railway Server)
```bash
# Clone and launch full production stack
git clone https://github.com/Mayank8159/TrackChain.git
cd TrackChain
docker-compose up -d --build
```

### Backend Production Environment Variables:

| Variable | Description | Production Example |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Target deployment environment | `production` |
| `DATABASE_URL` | PostgreSQL / TimescaleDB connection URI | `postgresql+psycopg2://user:pass@host:5432/trackchain` |
| `JWT_SECRET_KEY` | 256-bit cryptographically secure secret | `a8f5b4...` (generate with `openssl rand -hex 32`) |
| `CORS_ORIGINS` | Comma-separated allowlist of frontend URLs | `https://trackchain.vercel.app,http://localhost:3000` |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Ingestion throttle per edge device | `60` |

---

## 4. Database Migrations

Run Alembic migrations to initialize or upgrade the database schema:
```bash
cd backend
alembic upgrade head
```

---

## 5. Post-Deployment Verification (Smoke Test)

Run the automated remote smoke test against the live deployment:
```bash
./scripts/remote_smoke.sh https://your-backend.onrender.com
```

Expected output:
```text
=== TrackChain Remote Smoke Test ===
Target: https://your-backend.onrender.com

[1/3] Testing /health...
  ✓ PASSED (Status: 200 OK)

[2/3] Testing /api/sessions...
  ✓ PASSED (Status: 200 OK)

[3/3] Testing /api/alerts/stream (SSE)...
  ✓ PASSED (text/event-stream verified)

=== All tests passed! Backend is healthy. ===
```
