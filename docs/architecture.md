# TrackChain Master System Architecture Specification

> **Autonomous Railway Track Anomaly Intelligence, Predictive Maintenance & 3D Digital Twin Platform**  
> *Compliant with RDSO Comprehensive Track Inspection (CTI) & EN 13848-1 Track Geometry Standards*

---

## 1. End-to-End System Topology

The TrackChain platform is a distributed, edge-to-cloud cyber-physical system designed for real-time railway inspection, automated geometry classification, predictive degradation forecasting, and multi-user incident response.

```mermaid
flowchart TB
    %% ========================================================================
    %% 1. EDGE SENSING & INFERENCE LAYER
    %% ========================================================================
    subgraph EDGE["1. Edge Inspection Vehicle & Sensor Layer (RPi 5 & Jetson Orin)"]
        direction TB
        CAM["4K Global-Shutter Optical Camera\n(Sony IMX477 @ 60 FPS)"]
        IMU["6-DOF Inertial Measurement Unit\n(ICM-42688-P @ 100 Hz)"]
        GNSS["Dual-Antenna RTK GNSS Receiver\n(u-blox ZED-F9P ±0.05m Fix)"]
        
        subgraph EDGE_ML["Edge AI Perception Engine"]
            HOUGH["OpenCV Hough Transform\n(Rail & Sleeper Geometry)"]
            YOLO["YOLOv8-Rail Inference\n(Fasteners, Cracks, Squats)"]
            PATCH["PatchCore & Sequence-VAE\n(Unsupervised Visual & Spatial Novelty)"]
            PHYS["EN 13848-1 Physics Calculator\n(Twist, Gauge Widening, Cant)"]
        end
        
        BUFFER["Offline Circular SQLite WAL Buffer\n(Zero Data Loss in Tunnels)"]
        
        CAM --> HOUGH
        CAM --> YOLO
        CAM --> PATCH
        IMU --> PHYS
        GNSS --> PHYS
        
        HOUGH --> BUFFER
        YOLO --> BUFFER
        PATCH --> BUFFER
        PHYS --> BUFFER
    end

    %% ========================================================================
    %% 2. SECURE TRANSPORT LAYER
    %% ========================================================================
    subgraph TRANSPORT["2. Resilient Transport Layer (Zero-Trust Backhaul)"]
        direction TB
        TLS["Mutual TLS 1.3 / HTTPS Gateway\n(HMAC-SHA256 Request Signing)"]
        BUFFER -. "Telemetry Batch Ingest (100Hz)\n[X-Signature, X-Device-ID]" .-> TLS
        BUFFER -. "Defect Event Alert (Real-time)\n[Idempotency Key]" .-> TLS
        BUFFER -. "Multipart Media Chunk Upload" .-> TLS
    end

    %% ========================================================================
    %% 3. BACKEND CORE & PERSISTENCE
    %% ========================================================================
    subgraph BACKEND["3. Backend Core Platform (FastAPI & TimescaleDB Cloud)"]
        direction TB
        ROUTER["FastAPI Asynchronous Gateway\n(/api/telemetry, /api/defects, /api/alerts)"]
        ORCH["Fusion & Decision Engine\n(Multi-Modal Persistence Rules)"]
        
        subgraph STORAGE["Multi-Model Storage Tier"]
            TIMESCALE["TimescaleDB (PostgreSQL 14)\n(Hypertables: Telemetry, ML Signals)"]
            POSTGIS["PostGIS Spatial Extension\n(Indexed Linear Chainage Coordinates)"]
            MINIO["AWS S3 / MinIO Object Storage\n(HLS Video Segments & Raw Frames)"]
            REDIS["Redis In-Memory Bus\n(SSE Broadcast & Rate Limiter)"]
        end
        
        TLS --> ROUTER
        ROUTER --> ORCH
        ORCH --> TIMESCALE
        ORCH --> POSTGIS
        ROUTER --> MINIO
        ORCH --> REDIS
    end

    %% ========================================================================
    %% 4. MISSION CONTROL FRONTEND
    %% ========================================================================
    subgraph FRONTEND["4. Holographic SCADA Mission Control (Next.js 14 & R3F)"]
        direction TB
        
        subgraph MODULES["Operational Workspaces"]
            SCADA["/ (Mission Control Room)\nLive Corridor KPI & Speed Restrictions"]
            TWIN["/digital-twin (3D Digital Twin)\nProcedural Rails & Instanced Sleepers (R3F)"]
            ORACLE["/forecast (Predictive Oracle)\nConformal Degradation & TQI Recovery Curve"]
            WARROOM["/warroom/[id] (Incident War Room)\nSpatial Pinning, Flags & Voice Briefings"]
            MAP_VIEW["/map (GIS Corridor Map)\nLeaflet CartoDB TQI Polylines"]
            BENCH["/lab (Model Test Bench)\nReal-time Inference & Hough Overlays"]
            PERF["/performance (SRE Observatory)\n5-Stage Latency & Reliability Grade"]
            DEVICES_VIEW["/devices (Edge Fleet Manager)\nNode Onboarding & Hardware Provisioning"]
        end

        ROUTER -- "REST API Contracts (tc.v1)" --> FRONTEND
        REDIS -- "SSE Live Alert Stream (/api/alerts/stream)" --> SCADA
        MINIO -- "HLS Video Stream (.m3u8)" --> TWIN
    end

    %% Styling
    classDef edgeStyle fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef transStyle fill:#020617,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;
    classDef backStyle fill:#090d16,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef frontStyle fill:#050c1a,stroke:#06b6d4,stroke-width:2px,color:#f8fafc;
    
    class EDGE edgeStyle;
    class TRANSPORT transStyle;
    class BACKEND backStyle;
    class FRONTEND frontStyle;
```

---

## 2. Layer Specifications & Protocols

### 2.1 Edge Layer (Inspection Bogies & Revenue Locomotives)
- **Hardware Architecture**: Dual-compute setup pairing a Raspberry Pi 5 (telemetry aggregation, EN 13848-1 geometry math, GNSS sync) with an NVIDIA Jetson Orin Nano (4K vision inference).
- **Sampling Rates**:
  - IMU (Vibration, Roll, Pitch): **100 Hz** (uniform 0.25m spatial binning)
  - Vision (Optical Rails & Fasteners): **60 FPS** at 1080p / 15 FPS at 4K
  - GNSS (Centimetric Waypoint Sync): **10 Hz** RTK fix
- **Zero Data Loss Guarantee**: Local SQLite circular Write-Ahead Log (WAL) buffers up to 72 hours of inspection data during tunnel traversals or cellular dead zones, automatically resuming sync upon reconnection.

### 2.2 Transport & Security Layer
- **Zero-Trust Network Architecture**: Every request is authenticated via device-specific API keys or 60-minute scoped JWT tokens (`POST /api/v1/devices/token`).
- **Cryptographic Integrity**: Payloads are timestamped and signed with HMAC-SHA256 headers (`X-Signature`, `X-Timestamp`, `X-Device-ID`) to prevent replay attacks and tampering.
- **Data Source State Machine**: Frontend enforces explicit data source states (`DEMO ↔ REAL`) with visual HUD watermarks and strictly prohibits silent mock fallbacks during production telemetry ingestion.

### 2.3 Backend Core Platform
- **Framework**: FastAPI with asynchronous endpoints and Pydantic v2 contract enforcement (`tc.v1`).
- **Database Partitioning**:
  - **TimescaleDB**: Hypertables partitioned into 1-day chunks for high-throughput sensor telemetry (`telemetry_samples`) and model detections (`ml_signals`).
  - **PostGIS**: Spatial indexes (`idx_defect_events_lat_lon`, `idx_telemetry_lat_lon`) for bounding radius queries and track polyline generation.
  - **AWS S3 / MinIO**: Object storage for optical evidence clips and adaptive bitrate HLS ladders (`1080p`, `720p`, `480p`, `360p`).
  - **Redis Bus**: In-memory token bucket rate limiting (60 req/min/device) and Server-Sent Events (SSE) broadcasting.

### 2.4 Holographic SCADA Mission Control
- **Framework**: Next.js 14 (App Router) with React 18 and Tailwind CSS design tokens.
- **3D Digital Twin Engine**: React Three Fiber (R3F) and Three.js procedurally generating track geometry from raw EN 13848 telemetry, using `<instancedMesh>` to render 1,000+ sleepers in 1 draw call at 60 FPS.
- **Bi-Directional Synchronization**: Mathematical lockstep coordinating 3D fly-through cameras, 2D Recharts waveforms, and optical video scrubbing.
- **Multiplayer War Room**: Real-time collaborative triage with spatial map pins, video scrubber flags, voice note recording, and live presence avatars.
