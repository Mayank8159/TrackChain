# TrackChain Edge Node Onboarding & Ingestion Guide (tc.v1)

This technical specification details the hardware provisioning, cryptographic credential assignment, and telemetry streaming protocol for edge inspection nodes deployed across Indian Railways track inspection vehicles.

---

## 1. Hardware & System Prerequisites

| Subsystem | Requirement | Verified Hardware |
| :--- | :--- | :--- |
| **Compute Core** | Quad-core ARM64 / GPU Acceleration | Raspberry Pi 5 (8GB) / NVIDIA Jetson Orin Nano (8GB) |
| **Operating System** | Linux (Debian 12 / Ubuntu 22.04 LTS) | TrackChain Edge OS v2.5.0-prod |
| **Inertial Measurement** | 6-DOF IMU (Accelerometer & Gyroscope) | MPU-9250 / ADIS16470 (1 kHz sampling rate) |
| **Spatial GNSS** | Multi-Band L1/L2 RTK GNSS Receiver | u-blox ZED-F9P (Centimeter-level RTK Fix) |
| **Optical Sensor** | Global Shutter Camera (1080p @ 60 FPS) | Sony IMX296 / Flir Blackfly S USB3 |
| **Network Backhaul** | 4G/5G Cellular Modem with Dual-SIM Failover | Quectel RM500Q-GL 5G NR M.2 |

---

## 2. Onboarding Workflow (Field Engineer)

### Step 1: Register Node via Mission Control
1. Open TrackChain Mission Control and navigate to `/devices`.
2. Click **`[Register Node (Wizard)]`** in the top header.
3. Provide the **Node Name** (e.g., `NDLS-Bogie-Scanner-04`), **Hardware Profile**, **Serial Number**, and **Physical Mounting Location**.
4. Click **"Generate Credentials"**.

### Step 2: Save Cryptographic API Key
* The system will issue a unique **Node ID** (e.g., `NODE-BOG-4892`) and a cryptographically secure **Bearer API Key** (`tc_live_...`).
* **Security Rule:** This key is hashed using SHA-256 server-side. It will **never be shown again**. Copy and store it immediately in the device environment.

### Step 3: Configure Edge Node Environment
SSH into the target edge compute node and export the provisioned variables:

```bash
# /etc/trackchain/agent.env
export TRACKCHAIN_API_URL="https://trackchain-backend.onrender.com"
export TRACKCHAIN_DEVICE_ID="NODE-BOG-4892"
export TRACKCHAIN_API_KEY="tc_live_your_secret_api_key_here"
export INGEST_SAMPLING_RATE_HZ=100
```

### Step 4: Verify Handshake & Connectivity
Test connection from the edge terminal:
```bash
curl -s -H "Authorization: Bearer $TRACKCHAIN_API_KEY" \
     "$TRACKCHAIN_API_URL/health"
```
Expected response: `{"status": "ok", "service": "trackchain-backend"}`

### Step 5: Start the Systemd Ingestion Daemon
```bash
# Reload and enable the background daemon
sudo systemctl daemon-reload
sudo systemctl enable --now trackchain-agent

# Check live telemetry streaming logs
sudo journalctl -u trackchain-agent -f
```

---

## 3. Telemetry Streaming Protocol

### A. 100 Hz IMU & Kinematics Batch Ingest
Edge units buffer sensor readings into 1-second batches and post to `/api/telemetry`:

```http
POST /api/telemetry HTTP/1.1
Host: trackchain-backend.onrender.com
Authorization: Bearer tc_live_...
X-Device-ID: NODE-BOG-4892
Content-Type: application/json

{
  "session_id": "ses-delhi-agra-001",
  "device_id": "NODE-BOG-4892",
  "samples": [
    {
      "timestamp": "2026-08-21T06:00:00.010Z",
      "chainage_m": 21950.4,
      "accel_x_g": 0.02,
      "accel_y_g": 0.05,
      "accel_z_g": 1.08,
      "gyro_x_dps": 0.12,
      "gyro_y_dps": 0.08,
      "gyro_z_dps": -0.04,
      "speed_kmh": 128.4,
      "gauge_mm": 1676.2,
      "cant_mm": 42.1,
      "twist_mm_per_m": 1.8
    }
  ]
}
```

### B. High-Priority Defect Ingest & SSE Dispatch
When onboard YOLOv8 or EN 13848-1 geometry filter detects an anomaly:

```http
POST /api/defects HTTP/1.1
Host: trackchain-backend.onrender.com
Authorization: Bearer tc_live_...
Content-Type: application/json

{
  "session_id": "ses-delhi-agra-001",
  "device_id": "NODE-BOG-4892",
  "severity": "critical",
  "defect_class": "twist_exceedance",
  "chainage_m": 21950,
  "confidence": 0.94,
  "source_model": "EN13848-GeometryEngine",
  "latitude": 28.5244,
  "longitude": 77.2066
}
```

---

## 4. Operational Troubleshooting Matrix

| HTTP Status / Symptom | Root Cause | Remediation Procedure |
| :--- | :--- | :--- |
| **`401 Unauthorized`** | Expired or invalid API key | Re-open `/devices` wizard, generate new credentials, update `/etc/trackchain/agent.env`. |
| **`403 Forbidden`** | Scope restriction or revoked device | Check `/devices` dashboard to verify device status is not in `revoked` state. |
| **`429 Too Many Requests`** | Exceeded 60 req/min rate limit | Increase batch size from 100ms to 1000ms buffers to reduce HTTP request frequency. |
| **`503 Service Degraded`** | Circuit breaker tripped | Backend is temporarily buffering data; edge daemon auto-queues records locally in SQLite. |
| **DNS Resolution Failed** | Modem lost cellular connection | Daemon checks `ping 8.8.8.8` and falls back to secondary e-SIM interface. |
