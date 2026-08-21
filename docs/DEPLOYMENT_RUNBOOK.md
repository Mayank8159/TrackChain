# TrackChain Production Deployment Runbook

> **Step-by-step instructions for deploying TrackChain in Local Docker, Cloud VPS, and Vercel environments.**

---

## 1. Prerequisites & System Requirements

- **Server / VPS**: Linux (Ubuntu 22.04 LTS / Debian 12 / macOS), 4+ vCPU, 8 GB+ RAM, 50 GB+ NVMe SSD.
- **Tools Installed**:
  - Docker & Docker Compose (v2.20+)
  - Node.js 18.x or 20.x + `pnpm` (v9+ or v11+)
  - Python 3.11+ with `venv`
  - PostgreSQL client (`psql` v14+)

---

## 2. Environment Variables Matrix

| Variable | Scope | Description | Production Example |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Backend | Connection string for TimescaleDB | `postgresql://trackchain:secret@db.internal:5432/trackchain_db` |
| `REDIS_URL` | Backend | Redis URL for SSE broadcasting | `redis://redis.internal:6379/0` |
| `S3_ENDPOINT_URL` | Backend | S3 API endpoint (AWS or MinIO) | `https://s3.ap-south-1.amazonaws.com` |
| `S3_ACCESS_KEY` | Backend | S3 / MinIO access key | `AKIAIOSFODNN7EXAMPLE` |
| `S3_SECRET_KEY` | Backend | S3 / MinIO secret key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `S3_BUCKET_NAME` | Backend | Media assets bucket name | `trackchain-media-prod` |
| `API_KEY_SECRET` | Backend | Secret for device registration HMAC | `6f8d3b7e4a1c...` (Min 32 chars) |
| `JWT_SECRET_KEY` | Backend | Secret for 60-minute device JWTs | `a9c1e3f5...` (Min 64 chars) |
| `ENVIRONMENT` | Backend | Runtime mode | `production` |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend API base URL for client | `https://api.trackchain.internal` |

---

## 3. Backend Deployment (Docker Compose)

### 3.1 Quick Start with Docker
```bash
# 1. Clone repository
git clone https://github.com/Mayank8159/TrackChain.git
cd TrackChain

# 2. Copy environment template
cp backend/.env.example backend/.env

# 3. Spin up full containerized stack (TimescaleDB, Redis, MinIO, Backend)
docker-compose up -d --build

# 4. Verify container health
docker-compose ps
```

### 3.2 Bare-Metal / Native Python Setup
```bash
# 1. Initialize PostgreSQL database and user
./scripts/init_db.sh

# 2. Setup Python virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run Alembic database migrations
alembic upgrade head

# 4. Start production Uvicorn server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3.3 Backend Health Check
```bash
curl -i http://localhost:8000/health
# Expected: 200 OK -> {"status": "ok", "service": "trackchain-backend", "database": "connected"}
```

---

## 4. Frontend Deployment (Vercel)

### 4.1 Automated Vercel Deployment
1. Import the repository into your Vercel team account.
2. Set **Root Directory** to `app`.
3. Set **Framework Preset** to `Next.js`.
4. Configure Environment Variables in Vercel Project Settings:
   - `NEXT_PUBLIC_API_URL`: Your deployed FastAPI backend URL (e.g. `https://api.trackchain.railways.gov.in`).
5. Click **Deploy**.

### 4.2 Manual / Self-Hosted Node.js Server
```bash
cd app

# 1. Install dependencies
pnpm install

# 2. Compile optimized production build
pnpm build

# 3. Start standalone production server
pnpm start -p 3000
```

---

## 5. Edge Node Provisioning & Fleet Onboarding

1. **Flash Image**: Flash Ubuntu 22.04 LTS (Server or Desktop) onto Raspberry Pi 5 or NVIDIA Jetson Orin Nano.
2. **Launch Node Onboarding**: Navigate to [`/devices`](http://localhost:3000/devices) on the Mission Control dashboard.
3. **Generate Provisioning Token**:
   - Click **"+ Provision New Node"**.
   - Enter Device Name (e.g. `RPi5-Bogie-NDLS-04`).
   - Assign Device Roles (`telemetry_collector`, `vision_inference`).
   - Copy the generated one-line registration curl script.
4. **Execute on Edge Node**:
   ```bash
   curl -sSL https://api.trackchain.internal/scripts/bootstrap_node.sh | \
     sudo bash -s -- --token "TC_PROV_94a7f1..." --server "https://api.trackchain.internal"
   ```
5. **Verify Telemetry Stream**: Check `/devices` to verify the node appears as **ONLINE** with active battery and temperature readings.

---

## 6. Operational Disaster Recovery & Backups

- **Database Backup**:
  ```bash
  pg_dump -U trackchain -h localhost -d trackchain_db -Fc > "trackchain_backup_$(date +%Y%m%d_%H%M%S).dump"
  ```
- **Database Restore**:
  ```bash
  pg_restore -U trackchain -h localhost -d trackchain_db -c "trackchain_backup_XXXX.dump"
  ```
- **MinIO / S3 Sync**:
  ```bash
  aws --endpoint-url http://localhost:9000 s3 sync s3://trackchain-media ./backup_media/
  ```
