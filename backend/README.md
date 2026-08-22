# TrackChain Backend & Edge Node Infrastructure

TrackChain is a high-throughput, edge-to-cloud automated railway track inspection and predictive maintenance platform. The backend is designed for high-concurrency ingestion of high-resolution video streams and high-frequency inertial measurement unit (IMU) telemetry from trackside inspection vehicles, drones, and edge nodes (Raspberry Pi, Jetson Nano, ESP32).

---

## 1. System Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       EDGE HARDWARE TIER                                │
│                                                                         │
│  ┌───────────────────────┐              ┌─────────────────────────┐    │
│  │   Raspberry Pi /      │              │       ESP32-CAM         │    │
│  │   Jetson Nano / PC    │              │   Microcontroller       │    │
│  │ (Universal Py Agent)  │              │     (C++ Firmware)      │    │
│  └───────────┬───────────┘              └────────────┬────────────┘    │
└──────────────┼───────────────────────────────────────┼──────────────────┘
               │                                       │
               │ WSS (WebSocket Secure) + JWT Token    │
               ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS CLOUD TIER                                 │
│                                                                         │
│                    ┌───────────────────────────┐                        │
│                    │ AWS ALB / API Gateway     │                        │
│                    │ (SSL/TLS Termination)     │                        │
│                    └─────────────┬─────────────┘                        │
│                                  │ Internal VPC                         │
│                                  ▼                                      │
│                    ┌───────────────────────────┐                        │
│                    │  FastAPI Ingestion Gateway│                        │
│                    │      (/ws/node)           │                        │
│                    └──────┬─────────────┬──────┘                        │
│                           │             │                               │
│             Raw JPEG Bytes│             │ IMU JSON Payload              │
│       ┌───────────────────┴──────┐      │                               │
│       ▼                          ▼      ▼                               │
│ ┌───────────┐              ┌───────────────┐                            │
│ │ Async S3  │              │ In-Memory ML  │                            │
│ │ Upload    │              │ Queues (Zero- │                            │
│ │ Task      │              │ Latency RAM)  │                            │
│ └─────┬─────┘              └───┬───────┬───┘                            │
│       │                        │       │                                │
│       ▼                        ▼       ▼                                │
│ ┌───────────┐              ┌───────┐ ┌───────────┐                      │
│ │  AWS S3   │              │ ONNX  │ │ EN 13848  │                      │
│ │  Bucket / │              │ Vision│ │ Physics   │                      │
│ │Local Media│              │ Model │ │ Engine    │                      │
│ └───────────┘              └───┬───┘ └─────┬─────┘                      │
│                                │           │                            │
│                                └─────┬─────┘                            │
│                                      ▼                                  │
│                        ┌───────────────────────────┐                    │
│                        │ Defect & Telemetry Events │                    │
│                        └──────┬─────────────┬──────┘                    │
│                               │             │                           │
│                               ▼             ▼                           │
│                    ┌─────────────┐   ┌─────────────┐                    │
│                    │ PostgreSQL/ │   │  Live SSE / │                    │
│                    │ TimescaleDB │   │  WebSocket  │                    │
│                    │ (PostGIS)   │   │  Broadcast  │                    │
│                    └─────────────┘   └──────┬──────┘                    │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │     TRACKCHAIN FRONTEND     │
                               │   (Next.js SCADA & GIS Map) │
                               └─────────────────────────────┘
```

### Zero-Latency Ingestion Design
1. **Base64 Decode in Memory**: Inbound frame payloads from WebSockets are decoded directly into JPEG byte buffers in RAM.
2. **Dual-Path Routing**:
   - **Real-Time ML Path**: Raw image bytes and IMU readings are pushed directly into in-memory `asyncio.Queue` buffers (`frame_q`, `imu_q`) for sub-10ms inference and SSE live broadcasting.
   - **Durable Storage Path**: An asynchronous background task (`asyncio.create_task`) streams the frame to AWS S3 (or local media fallback in `/tmp/trackchain-media/`) without blocking the ingestion loop.
3. **Chainage Tracking**: Every packet is indexed with real-time linear chainage (track kilometer marker) computed from speed sensors or GPS timestamps.

---

## 2. Directory Structure

```
backend/
├── Dockerfile                  # Production container for AWS ECS Fargate
├── Dockerfile.dev              # Hot-reload container for local development
├── Dockerfile.lambda           # Container packaging for AWS Lambda / Mangum
├── alembic.ini                 # Database migration configuration
├── pyproject.toml              # Project metadata and tool configuration
├── requirements.txt            # Core production dependencies
├── requirements.cloud.txt      # Lambda/Cloud-optimized lightweight dependencies
├── samconfig.toml              # AWS SAM CLI deployment parameters
├── template.yaml               # CloudFormation Serverless Application Model (SAM)
├── scripts/                    # Unified lifecycle and automation scripts
│   ├── build.sh                # Container & Lambda layer builder
│   ├── run.sh                  # Local development server orchestrator
│   ├── test.sh                 # Test runner (pytest)
│   ├── migrate.sh              # Database migration runner (Alembic)
│   ├── init_db.sh              # Database schema & PostGIS initializer
│   ├── deploy_docker.sh        # Docker deployment runner
│   ├── deploy_docker.ps1       # Windows PowerShell deployment runner
│   ├── prod_launch.sh          # Production stack launcher
│   ├── prod_launch.ps1         # Windows PowerShell production launcher
│   ├── remote_smoke.sh         # Smoke test against deployed endpoints
│   ├── seed.py                 # Core database seeder
│   └── seed_real_session.py    # High-density real TRC session seeder
└── src/
    ├── main.py                 # FastAPI application factory & Mangum handler
    ├── config.py               # Pydantic v2 Settings loader (.env parsing)
    ├── api/                    # REST API routing
    │   ├── deps.py             # Dependency injection (DB session, Auth)
    │   └── routes/             # Feature route controllers
    │       ├── alerts.py       # Notification and alert management
    │       ├── dashboard.py    # Analytics and aggregated metrics
    │       ├── defects.py      # Rail defect query and manual reporting
    │       ├── devices.py      # Node registration and lifecycle
    │       ├── health.py       # System health & liveness probes
    │       ├── ingest.py       # Direct HTTP ingestion endpoints
    │       ├── media.py        # S3 presigned URL generation and playback
    │       ├── ml.py           # On-demand ML model inference
    │       ├── sessions.py     # Track recording session management
    │       └── telemetry.py    # Geospatial track geometry query endpoints
    ├── core/                   # Shared types and logging configuration
    ├── db/                     # Database layer
    │   ├── base.py             # SQLAlchemy Base declaration
    │   ├── models.py           # PostgreSQL/TimescaleDB ORM models
    │   ├── session.py          # Connection pooling & session maker
    │   └── migrations/         # Alembic database migrations
    ├── gateway/                # WebSocket endpoints
    │   ├── node_ws.py          # Edge node ingestion & adaptive throttling
    │   └── live_ws.py          # Real-time frontend SCADA broadcasting
    ├── schemas/                # Pydantic validation schemas
    ├── services/               # Core business and engineering logic
    │   ├── alerts.py           # Real-time alert dispatch
    │   ├── artifacts.py        # Model checkpoint loader
    │   ├── audit.py            # Compliance and audit logging
    │   ├── auth.py             # JWT token issuance, verification, scopes
    │   ├── chainage.py         # Linear track positioning engine
    │   ├── circuit_breaker.py  # Fault tolerance & failover handler
    │   ├── ingest.py           # In-memory queue managers (frame_q, imu_q)
    │   ├── observability.py    # Prometheus metrics & X-Ray tracing
    │   ├── onnx_inference.py   # Ultralytics & ONNX runtime inference
    │   ├── pipeline.py         # Background ML & EN 13848 processing worker
    │   ├── rate_limiter.py     # Token-bucket rate limiting per device
    │   └── s3.py               # S3 upload with local fallback
    └── tasks/                  # Celery/Background task definitions
```

---

## 3. Setup & Orchestration Scripts (`backend/scripts/`)

All scripts in `backend/scripts/` follow strict bash conventions (`set -euo pipefail`) and standardized color-coded output that mirrors the `ml/scripts/` architecture.

| Script | Purpose | Usage |
| :--- | :--- | :--- |
| `run.sh` | Sets up venv, installs requirements, exports `.env`, and launches Uvicorn on port `8000`. | `./scripts/run.sh` |
| `build.sh` | Builds the production Docker image (`trackchain-backend:latest`) and packages the Lambda zip layer. | `./scripts/build.sh` |
| `test.sh` | Executes the test suite via `pytest` with concise traceback formatting. | `./scripts/test.sh` |
| `migrate.sh` | Applies Alembic migrations (`head`) or generates new auto-migrations. | `./scripts/migrate.sh [create "name"]` |
| `init_db.sh` | Connects to PostgreSQL, activates PostGIS/TimescaleDB extensions, and applies DDL. | `./scripts/init_db.sh` |
| `deploy_docker.sh` | Spins up the containerized service stack using Docker Compose. | `./scripts/deploy_docker.sh` |
| `prod_launch.sh` | Validates environment configurations, applies migrations, and executes production startup. | `./scripts/prod_launch.sh` |
| `remote_smoke.sh` | Runs health, telemetry, and defect endpoint sanity tests against a deployed URL. | `./scripts/remote_smoke.sh <BASE_URL>` |
| `seed.py` | Seeds the database with default devices, sessions, defect catalogues, and sample tracks. | `python scripts/seed.py` |
| `seed_real_session.py`| Seeds realistic high-density track recording runs with EN 13848 geometry signals. | `python scripts/seed_real_session.py` |

---

## 4. Edge Node Architecture & Microprocessor Setup

TrackChain provides two production-grade edge clients:
1. **Universal Python Node Agent (`edge/agent/`)**: For SBCs (Raspberry Pi 4/5, Jetson Nano/Orin) and industrial PCs.
2. **C++ Firmware Protocol Contract (`edge/trackchain_node/`)**: For low-cost ESP32-CAM microcontrollers.

---

### A. Universal Python Edge Node Agent (`edge/agent/`)

The Python agent automatically detects physical I2C sensors and falls back gracefully to a synthetic vibration generator on development machines.

```
edge/agent/
├── edge_node.py          # Main asyncio node agent runtime
├── node_config.yaml      # Hardware & network configuration
└── requirements.txt      # Python dependencies (websockets, opencv, pyyaml, smbus2)
```

#### 1. Hardware Wiring (Raspberry Pi / Jetson Nano)
* **Camera**: Connect USB 2.0/3.0 Webcam to USB port, or attach Raspberry Pi Camera Module v2/v3 via the CSI ribbon cable.
* **IMU (MPU6050 / BNO055)**: Connect to the I2C bus:
  * `VCC` $\rightarrow$ Pin 1 (`3.3V Power`)
  * `GND` $\rightarrow$ Pin 6 (`Ground`)
  * `SDA` $\rightarrow$ Pin 3 (`GPIO 2 / I2C1 SDA`)
  * `SCL` $\rightarrow$ Pin 5 (`GPIO 3 / I2C1 SCL`)

*Enable I2C on Raspberry Pi OS:*
```bash
sudo raspi-config
# Select: Interface Options -> I2C -> Enable -> Finish
sudo reboot
```

#### 2. Software Installation
```bash
cd edge/agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Configuration (`node_config.yaml`)
```yaml
node_id: "TC-NODE-PI-01"
backend_wss: "ws://localhost:8000/ws/node" # Or wss://api.trackchain.your-domain.com/ws/node
auth_token: "SECRET_TOKEN"                  # Provisioned JWT token from backend

hardware:
  camera:
    enabled: true
    source: 0             # 0 for /dev/video0, or RTSP URL
    fps: 5                # Target framerate
    quality: 75           # JPEG quality (1-100)
  imu:
    enabled: true
    hz: 20                # IMU sample rate (Hz)
    mock_if_missing: true # Fallback to realistic synthetic telemetry if no I2C chip found

network:
  store_and_forward: true
  buffer_size: 5000       # Ring buffer capacity during 4G/LTE drops
```

#### 4. Production Systemd Service (`systemd`)
To ensure resilient, auto-restarting operation on physical inspection vehicles:

Create `/etc/systemd/system/trackchain-node.service`:
```ini
[Unit]
Description=TrackChain Universal Edge Node Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/TrackChain/edge/agent
ExecStart=/home/pi/TrackChain/edge/agent/venv/bin/python edge_node.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/trackchain-node.log
StandardError=append:/var/log/trackchain-node-error.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trackchain-node
sudo systemctl start trackchain-node
sudo systemctl status trackchain-node
```

---

### B. ESP32-CAM Microcontroller Setup (C++ Firmware)

For ultra-compact installations (e.g. bogie-mounted miniature inspection nodes), TrackChain supports the ESP32-CAM with the exact same JSON WebSocket protocol.

#### Hardware Pinout (AI-Thinker ESP32-CAM):
* `SDA` $\rightarrow$ `GPIO 26`
* `SCL` $\rightarrow$ `GPIO 27`
* Camera Interface: OV2640 2MP CMOS sensor.

#### Firmware Compilation (`edge/trackchain_node/trackchain_node.ino`):
* **Required Libraries**: `WebSocketsClient`, `ArduinoJson` (v6+), `Adafruit_MPU6050`, `Adafruit_Sensor`.
* **Configuration**: Set `WIFI_SSID`, `WIFI_PASS`, `WS_HOST`, and `NODE_TOKEN` in the source file.
* Compile and flash using the Arduino IDE or PlatformIO with partition scheme `Huge APP (3MB No OTA / 1MB SPIFFS)`.

---

## 5. Protocol Specification (Edge $\leftrightarrow$ AWS Gateway)

All nodes communicate using unified JSON frames over WebSocket (`/ws/node?token=<JWT>`).

### 1. Connection Handshake (`hello`)
Sent by the edge node immediately upon connection:
```json
{
  "type": "hello",
  "node_id": "TC-NODE-PI-01",
  "caps": {
    "cam": 1,
    "imu": 1
  }
}
```
**Backend Response (`cfg`)**:
```json
{
  "type": "cfg",
  "fps": 5,
  "imu_hz": 20
}
```

### 2. Camera Frame Stream (`frame`)
```json
{
  "type": "frame",
  "seq": 1042,
  "t": 1718900123456,
  "w": 640,
  "h": 480,
  "b64": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBD..."
}
```

### 3. IMU Telemetry Stream (`imu`)
```json
{
  "type": "imu",
  "seq": 5210,
  "t": 1718900123456,
  "ax": 0.042,
  "ay": -0.015,
  "az": 9.814,
  "gx": 0.001,
  "gy": -0.002,
  "gz": 0.0005
}
```

### 4. Heartbeat (`hb`)
Sent every 5 seconds to maintain active node status:
```json
{
  "type": "hb",
  "t": 1718900123456
}
```
**Backend Ack (`ack`)**:
```json
{
  "type": "ack",
  "t": 1718900123456
}
```

---

## 6. Environment Configuration (`backend/.env`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Deployment stage (`development`, `staging`, `production`) | `development` |
| `DATABASE_URL` | PostgreSQL / TimescaleDB connection URI | `postgresql+psycopg2://user:pass@host:5432/trackchain` |
| `STORAGE_BACKEND` | Storage backend type (`s3` or `local`) | `s3` |
| `S3_ENDPOINT_URL` | AWS S3 or MinIO custom endpoint URL | `https://s3.us-east-1.amazonaws.com` |
| `S3_BUCKET_NAME` | Media evidence storage bucket | `trackchain-media` |
| `S3_REGION` | AWS Region | `us-east-1` |
| `S3_ACCESS_KEY` | AWS IAM Access Key ID | `AKIA...` |
| `S3_SECRET_KEY` | AWS IAM Secret Access Key | `...` |
| `JWT_SECRET_KEY` | Secret for verifying node & client JWTs | `trackchain-jwt-secret-key` |
| `API_KEY_SECRET` | Secret for device registration API keys | `trackchain-api-secret-key` |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend domains | `http://localhost:3000,https://trackchain.vercel.app` |

---

## 7. Cloud Deployment (AWS ECS Fargate & SAM Lambda)

### A. AWS ECS Fargate Deployment
The primary production deployment runs as an ECS Fargate service behind an Application Load Balancer (ALB) with sticky sessions / WebSocket support enabled:
```bash
# Build and tag image
docker build -t trackchain-backend:latest -f Dockerfile .

# Authenticate with Amazon ECR and push
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
docker tag trackchain-backend:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/trackchain-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/trackchain-backend:latest
```

### B. AWS SAM Lambda Serverless Deployment
For serverless deployments using API Gateway HTTP/REST API and AWS Lambda:
```bash
sam build --use-container
sam deploy --guided
```

---

## 8. Verification & Quickstart

To run the complete system locally:

1. **Start the Database**:
   ```bash
   docker compose up -d
   ```
2. **Launch the Backend API & Gateway**:
   ```bash
   cd backend
   ./scripts/run.sh
   ```
3. **Run the Edge Node Agent**:
   ```bash
   cd edge/agent
   python edge_node.py
   ```
4. **Inspect Live Stream & Endpoints**:
   * FastAPI Swagger Docs: `http://localhost:8000/docs`
   * Health Check: `http://localhost:8000/health`
   * Prometheus Metrics: `http://localhost:8000/metrics`
