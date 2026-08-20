# System architecture: app -> backend -> DB + S3, and the edge/ML data flow.

# TrackChain System Architecture

TrackChain is designed as a fault-tolerant, edge-to-cloud continuous monitoring and defect intelligence system for national railway networks.

---

## 🏗️ Monorepo Component Diagram

```mermaid
graph TD
    subgraph Edge ["Track Inspection Vehicle / Car"]
        CAM[Optical Cameras] --> RESAMPLE[Chainage Resampler]
        IMU[IMU / Accelerometers] --> RESAMPLE
        GNSS[RTK GNSS Receiver] --> RESAMPLE
        RESAMPLE --> V_STREAM[Vision Stream (YOLOv8 + PatchCore)]
        RESAMPLE --> G_STREAM[Geometry Stream (EN 13848 + Bi-LSTM)]
        V_STREAM --> FUSE[Rule & Persistence Fusion]
        G_STREAM --> FUSE
    end

    subgraph Cloud ["Central Infrastructure"]
        FUSE -->|Telemetry & Defect Events| API[FastAPI Backend]
        CAM -->|High-Res Video Frames| S3[MinIO / AWS S3 Media Bucket]
        API --> DB[(TimescaleDB / PostgreSQL)]
        API --> DASH[Next.js App Router Web UI]
    end
```

---

## 📦 Directory Overview
- **`app/`**: Next.js 14 Web Application featuring live SCADA control room, GIS map, and synchronized video playback.
- **`backend/`**: FastAPI high-throughput REST API with TimescaleDB time-series storage and AWS S3 integration.
- **`ml/`**: Two-stream Vision and Physics Geometry machine learning modules with temperature calibration and persistence fusion.
- **`packages/shared/`**: Canonical TypeScript DTO interfaces shared across applications.
- **`infra/`**: Docker container specifications and AWS IAM / S3 access policies.
- **`scripts/`**: Automation tooling for environment setup, database seeding, and development execution.
