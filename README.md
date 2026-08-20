# TrackChain monorepo overview, quickstart, and links to architecture and ML design docs.

# 🚄 TrackChain

> **Edge-Native Rail Anomaly Intelligence & Integrated Track Monitoring System**  
> Ministry of Railways — AI-powered defect detection, track geometry analytics, and continuous telemetry monitoring.

---

## 📌 Architecture Overview

TrackChain is a hybrid edge-to-cloud monorepo platform designed for high-frequency railway track health diagnostics.

```
┌─────────────────────────────────────────────────────────────┐
│                      TrackChain System                       │
├─────────────────┬───────────────────┬───────────────────────┤
│    app/         │     backend/      │         ml/           │
│ Next.js Web App │  FastAPI REST API │ Vision + Physics Geo  │
│ SCADA Dashboard │  TimescaleDB + S3 │ PatchCore + Bi-LSTM   │
└────────┬────────┴─────────┬─────────┴───────────┬───────────┘
         │                  │                     │
         └──────────────────┼─────────────────────┘
                            ▼
                  packages/shared (DTOs)
```

- **`app/`**: Modern Next.js 14 App Router dashboard with GIS track map, synchronized video playback, telemetry charts, and live SCADA control room.
- **`backend/`**: High-performance FastAPI service connected to PostgreSQL/TimescaleDB for time-series telemetry and S3/MinIO for raw imagery/video storage.
- **`ml/`**: Two-stream architecture:
  - *Vision Stream*: YOLOv8 discrete defect detector + PatchCore unsupervised surface anomaly detector.
  - *Geometry Stream*: Deterministic EN 13848 physics features (twist, cant, unevenness) + Bi-LSTM classifier + Sequence VAE.
  - *Fusion & Calibration*: Temperature scaling, FPR budgeting, and rule-based spatial/temporal persistence fusion.
- **`packages/shared/`**: Shared TypeScript contracts and canonical DTO interfaces across web and edge.
- **`infra/`**: Container configurations (Dockerfiles) and AWS deployment policies.
- **`scripts/`**: Automation scripts for setup, dev server launching, database seeding, and scaffolding.

---

## 🚀 Quick Start

### 1. Prerequisites
- Node.js >= 18 and `pnpm` >= 9
- Python >= 3.10 and `pip` / `virtualenv`
- Docker and Docker Compose (optional for local DB & MinIO)

### 2. Monorepo Setup

```powershell
# Run one-shot setup script
.\scripts\setup.ps1
```

Or manually:
```bash
pnpm install
cd backend && pip install -r requirements.txt
cd ../ml && pip install -r requirements.txt
```

### 3. Local Development

```powershell
# Start dev services
.\scripts\dev.ps1
```

- Web UI: [http://localhost:3000](http://localhost:3000)
- Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- MinIO Console: [http://localhost:9001](http://localhost:9001)

---

## 📚 Documentation
- [System Architecture](docs/architecture.md)
- [ML Two-Stream Design](docs/ml-design.md)
- [API Reference](docs/api.md)
- [Hardware & Sensor BOM](docs/hardware-bom.md)
