# TrackChain Production Launch Architecture & Operations Runbook

> **Target Platform**: Indian Railways Track Intelligence & SCADA Operations  
> **Schema Version**: `tc.v1`  
> **Infrastructure Grade**: Production / High-Availability / Mission-Critical  

---

## 1. Production Topology & High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                           TRACKCHAIN PRODUCTION SYSTEM TOPOLOGY                             │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  [Edge Fleet: Inspection Locomotives / Trolleys (Raspberry Pi 5 / Jetson Orin)]              │
│  ├── Multi-Modal AI Inference (YOLOv8n + PatchCore + EN 13848 + Bi-LSTM + Seq-VAE)          │
│  ├── Local S3 Presigned Multipart Uploader (Direct to S3 Bucket)                            │
│  └── Edge Emitter Client (HTTPS + Scoped JWT + HMAC-SHA256 Request Signing)                │
│                                │                                                             │
│                                ▼ (TLS 1.3 / 4G-5G Railway WAN)                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ AWS CloudFront CDN / AWS API Gateway (Rate Limiting + WAF DDoS Protection)            │  │
│  └─────────────────────────────┬─────────────────────────────────────────────────────────┘  │
│                                │                                                             │
│                                ▼                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Application Load Balancer (ALB) - Multi-AZ Target Groups                              │  │
│  └─────────────────────────────┬─────────────────────────────────────────────────────────┘  │
│                                │                                                             │
│                                ▼                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ FastAPI Container Cluster (AWS ECS Fargate / Kubernetes EKS)                           │  │
│  │ ├── Auto-scaling: 2–20 Pods based on CPU & Request Latency (Prometheus HPA)           │  │
│  │ ├── Middleware: RequestTraceMiddleware (X-Request-ID) + JWT Auth + Rate Limiter       │  │
│  │ ├── Service Layer: LTTB Downsampling + Video Transcoder + Webhook Dispatcher          │  │
│  │ └── Circuit Breakers: redis_breaker, s3_breaker, webhook_breaker (Fail-Fast HTTP 503)│  │
│  └───────────────────┬──────────────────────┬──────────────────────┬─────────────────────┘  │
│                      │                      │                      │                        │
│                      ▼                      ▼                      ▼                        │
│  ┌──────────────────────┐┌──────────────────────┐┌───────────────────────────────────────┐  │
│  │ TimescaleDB Cluster  ││ Redis Cluster (ElastiCache)│ AWS S3 Asset Lake (Multi-Tier)   │  │
│  │ - Primary (RW)       ││ - Rate Limit Counters│ - /raw_video/ (Standard -> Glacier)    │  │
│  │ - Read Replicas (RO) ││ - SSE Alert Broker   │ - /hls_streams/ (CloudFront Origin)    │  │
│  │ - Hypertables        ││ - Token Blacklist    │ - /evidence/ (Standard-IA)             │  │
│  │ - PostGIS Geometry   ││                      │ - /reports/ (CSV / Parquet Data Lake)  │  │
│  └──────────────────────┘└──────────────────────┘└───────────────────────────────────────┘  │
│                      │                                                                      │
│                      ▼                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ External Integrations & Observability                                                 │  │
│  │ ├── RDSO / UDM / TMS Webhooks (HMAC-SHA256 Signed + Exponential Backoff)             │  │
│  │ ├── Prometheus Metric Scraper (/metrics) -> Grafana Unified SCADA Dashboard          │  │
│  │ └── AWS CloudWatch / OpenSearch JSON Log Aggregator                                   │  │
│  └───────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Infrastructure Specifications

### 2.1 Compute Tier (FastAPI Engine)
- **Deployment Platform**: AWS ECS Fargate or Kubernetes (EKS).
- **Base Image**: Python 3.13-slim optimized with multi-stage Docker build.
- **ASGI Server**: Uvicorn worker pool managed by Gunicorn (`4 workers per vCPU`).
- **Scaling Triggers**:
  - Scale Up: Average CPU $> 70\%$ or P95 request latency $> 250\text{ ms}$.
  - Scale Down: Average CPU $< 30\%$ over 10 consecutive evaluation minutes.
- **High Availability**: Deployed across 3 Availability Zones (`ap-south-1a`, `ap-south-1b`, `ap-south-1c`).

### 2.2 Database Tier (TimescaleDB + PostgreSQL 16 + PostGIS)
- **Engine**: TimescaleDB on PostgreSQL 16.
- **Hypertables**:
  - `telemetry_samples`: Partitioned by `timestamp` into 1-day chunks.
  - `ml_signals`: Partitioned by `timestamp` into 1-day chunks.
- **Compression Policy**: Hypertables older than 7 days are automatically compressed into columnar format, reducing storage costs by $>85\%$.
- **Retention Policy**:
  - Raw 100Hz telemetry: Retained for 90 days.
  - LTTB-downsampled curves & defect events: Retained permanently for 10-year track lifecycle analysis.
- **Spatial Indexing**: PostGIS `GIST (geom)` indexes for sub-millisecond radius search (`/api/v1/defects/nearby`).

### 2.3 Object Storage Tier (AWS S3 + CloudFront CDN)
- **Storage Classes & Lifecycle Rules**:
  - `0–30 Days`: S3 Standard (Low-latency streaming & active inspection review).
  - `31–180 Days`: S3 Standard-Infrequent Access (Historical review).
  - `> 180 Days`: S3 Glacier Instant Retrieval (Compliance archives).
- **Streaming Pipeline**:
  - Uploaded MP4 video chunks trigger asynchronous multi-bitrate HLS transcoding (`1080p`, `720p`, `480p`, `360p`).
  - HLS segments (`.ts`) and playlists (`.m3u8`) are served through CloudFront with global edge caching.

---

## 3. Security, Authentication & Compliance

### 3.1 Edge Device Authentication Lifecycle
1. **Device Registration (`POST /api/v1/devices/register`)**:
   - Authorized hardware trolley is registered with UUID, camera model, and hardware specs.
   - Generates a high-entropy 256-bit API key (`tc_live_...`), hashed using SHA-256 in the database.
2. **JWT Access Token Exchange (`POST /api/v1/devices/token`)**:
   - Device exchanges its API key for a short-lived (60 min) HMAC-SHA256 JWT access token and a long-lived refresh token.
   - Access token contains claims: `sub` (device_id), `exp` (timestamp), `scopes` (`["telemetry:write", "defects:write"]`).
3. **HMAC-SHA256 Request Signing**:
   - Ingestion payloads are signed on the edge: $\text{Signature} = \text{HMAC-SHA256}(\text{Secret}, \text{Body} + \text{Timestamp})$.
   - Backend validates `X-Signature` and checks timestamp skew ($< 300\text{ seconds}$) to prevent replay attacks.
4. **Instant Revocation (`POST /api/v1/devices/revoke`)**:
   - Compromised or decommissioned devices are revoked immediately, blocking token exchange and invalidating existing sessions.

### 3.2 Regulatory Compliance & Webhook Integration
- **Indian Railways RDSO Compliance**:
  - Automatic dispatch of HMAC-signed alerts to RDSO Track Management System (TMS) and Unified Data Management (UDM) endpoints whenever critical geometry exceedances or missing fasteners are detected.
  - Export utilities generate RDSO standard CSV and Apache Parquet formats.
- **Immutable Audit Logging (`audit_logs` table)**:
  - All device registrations, configuration modifications, defect state transitions, and operator overrides are permanently recorded with actor ID, IP address, timestamp, and details JSON.

---

## 4. Reliability & Graceful Degradation

### 4.1 Circuit Breakers (`backend/src/services/circuit_breaker.py`)
- **Protected Dependencies**:
  - `redis_breaker`: Caches and rate limit counters.
  - `s3_breaker`: Media presigning and upload completion.
  - `webhook_breaker`: External RDSO/UDM webhook push delivery.
- **State Machine**:
  - Failure Threshold: 5 consecutive downstream errors trips the circuit to `OPEN`.
  - Recovery Timeout: 30 seconds before testing `HALF_OPEN` state.
  - Fail-Fast Response: Returns `HTTP 503 Service Unavailable` with `Retry-After: 30` header, shielding downstream systems from cascade failures.

### 4.2 Idempotency & Offline Resilience
- Edge trolleys operate in remote railway corridors with intermittent 4G cellular coverage.
- All ingestion endpoints (`/telemetry/batch`, `/ml/signals/batch`, `/defects`) require an `X-Idempotency-Key` header.
- Cached responses ensure duplicated network retries do not create duplicate defect alarms or corrupt time-series tables.

---

## 5. Observability & Monitoring Metrics

- **Scrape Endpoint**: `GET /metrics` (Prometheus OpenMetrics standard).
- **Core Metrics Matrix**:

| Metric Name | Type | Description |
|---|---|---|
| `trackchain_http_requests_total` | Counter | Requests by method, path, and HTTP status code |
| `trackchain_http_request_duration_seconds` | Histogram | Request latency with 11 buckets (0.005s to 10.0s) |
| `trackchain_defects_created_total` | Counter | Defects classified by defect class, severity, and source model |
| `trackchain_telemetry_samples_total` | Counter | Total IMU and track geometry points ingested |
| `trackchain_active_sessions` | Gauge | Currently running live inspection sessions |
| `trackchain_ml_inference_seconds` | Histogram | Inference latency tracked per ML model |

- **Request Tracing**: Every inbound request receives an `X-Request-ID` (UUID or edge-propagated trace ID), included in all structured JSON log records for distributed tracing.

---

## 6. Production Launch & Go-Live Runbook

### Step 1: Environment Configuration
Create production `.env` from template:
```bash
cp .env.example .env
```
Ensure production secrets are populated:
```ini
ENVIRONMENT=production
DATABASE_URL=postgresql://trackchain_admin:STRONG_PASSWORD@timescale-primary.internal:5432/trackchain_prod
JWT_SECRET_KEY=STRONG_RANDOM_SECRET_KEY_64_CHARACTERS
REQUEST_SIGNING_SECRET=STRONG_DEVICE_SIGNING_SECRET_KEY
S3_BUCKET_NAME=trackchain-prod-media-assets
AWS_REGION=ap-south-1
RDSO_WEBHOOK_URL=https://tms.indianrailways.gov.in/api/v1/alerts
RDSO_WEBHOOK_SECRET=STRONG_RDSO_HMAC_SECRET
```

### Step 2: Database Initialization & Migrations
```bash
# Execute schema initialization
python -c "from src.db.session import engine, Base; Base.metadata.create_all(bind=engine)"

# Run Alembic migrations
alembic upgrade head
```

### Step 3: Container Deployment
```bash
# Deploy containers via orchestrator
bash scripts/deploy_docker.sh
# or for Windows:
# .\scripts\deploy_docker.ps1
```

### Step 4: Health & Readiness Verification
```bash
# Verify liveness probe
curl -f http://localhost:8000/health

# Verify readiness probe (DB + S3 checks)
curl -f http://localhost:8000/health/ready

# Verify Prometheus metrics scrape
curl -f http://localhost:8000/metrics
```

### Step 5: Edge-to-Cloud Integration Smoke Test
```bash
python ml/scripts/emit_sample.py --backend-url http://localhost:8000
```
When `[SUCCESS] TrackChain Edge-to-Cloud Integration Slice Verified Successfully!` is displayed, the system is fully operational and certified for production traffic.
