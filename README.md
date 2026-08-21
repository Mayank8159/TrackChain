# 🚄 TrackChain (ITMS)

> **Autonomous Railway Track Anomaly Intelligence & Integrated SCADA Mission Control**  
> *Engineered for Indian Railways (Northern Railway Division) · Smart India Hackathon (SIH)*

[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg?style=flat-square)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14.2_App_Router-black.svg?style=flat-square)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110_Streaming_SSE-009688.svg?style=flat-square)](https://fastapi.tiangolo.com/)
[![Leaflet](https://img.shields.io/badge/GIS-Leaflet_CartoDB-199900.svg?style=flat-square)](https://leafletjs.com/)
[![Standards](https://img.shields.io/badge/Standards-RDSO_TMD_v2.4_%7C_EN_13848--1-critical.svg?style=flat-square)](http://www.rdso.indianrailways.gov.in/)

---

## 📌 Executive Summary

Indian Railways operates over **68,000 route kilometers**, where track health is critical to passenger safety and freight throughput. Traditional inspection relies on manual foot patrols and periodic recording cars that operate months apart, leaving tracks vulnerable to rapidly developing micro-geometry defects.

**TrackChain** is an edge-to-cloud autonomous inspection platform that bridges edge AI sensor heads mounted directly on revenue locomotives with a centralized SCADA Mission Control room. It executes real-time 4K optical computer vision and 100 Hz 3-axis IMU vibration telemetry fusion to detect, track, and triage rail flaws before catastrophic failure occurs.

---

## 🏛️ System Architecture

```mermaid
flowchart TB
    subgraph EDGE["Edge Computing Nodes (Inspection Vehicles)"]
        CAM["4K Global Shutter Vision Head\n(Sony IMX477 / Basler)"]
        IMU["6-DOF Inertial Sensor\n(ICM-42688-P @ 100Hz)"]
        GPS["Dual-Antenna RTK GNSS\n(u-blox ZED-F9P ±0.05m)"]
        
        YOLO["YOLOv8-Rail Inference\n(Surface Cracks & Fasteners)"]
        VAE["Sequence VAE + PatchCore\n(Out-of-Distribution Anomaly)"]
        GEO["EN 13848-1 Physics Engine\n(Twist, Gauge, Cant)"]
        
        CAM --> YOLO
        CAM --> VAE
        IMU --> GEO
        GPS --> GEO
    end

    subgraph BACKHAUL["Resilient 4G/5G Backhaul & Ingestion"]
        WAL["Local SQLite Circular Buffer\n(Tunnel Disconnection Tolerance)"]
        API["FastAPI High-Throughput Daemon\n(/api/alerts/stream SSE)"]
        WAL -. Automatic Reconnection Sync .-> API
        YOLO --> API
        VAE --> API
        GEO --> API
    end

    subgraph CORE["SCADA Mission Control (Next.js 14 App Router)"]
        DASH["/ (Operational Dashboard)\nRoute Line Diagram & Live KPI"]
        VIEWER["/sessions/[id] (Inspection Viewer)\nBi-directional Video ↔ Telemetry Sync"]
        DRAWER["AI Evidence Drawer\nHuman-in-the-Loop Feedback"]
        MAP["/map (GIS Track Corridor)\nLeaflet CartoDB TQI Polylines"]
        ALERTS["/alerts (Live Triage Center)\nWeb Audio Alarm Synthesizer"]
        REPORTS["/reports (RDSO TMD v2.4)\nCSV & Apache Parquet Exporter"]
        DEVICES["/devices (Edge Fleet)\nSensor Health & Cryptographic Keys"]
        
        API --> CORE
    end
```

---

## ⚡ Key Technical Differentiators

1. **Bi-Directional Video ↔ Telemetry Synchronization**:
   * Mathematical lockstep between 60s 4K video scrubbing and high-frequency Recharts telemetry waveforms with sub-millisecond precision.
2. **Deterministic EN 13848-1 Track Geometry Engine**:
   * Continuous computation of Immediate Action Limits (IAL) for track twist ($3.5\text{ mm/m}$ alert, $6.2\text{ mm/m}$ critical), gauge widening ($+13\text{mm}$), and vertical acceleration ($>2.2g$).
3. **Dual-Branch Hybrid AI Detection**:
   * Supervised YOLOv8 discrete flaw detection coupled with unsupervised Sequence VAE / PatchCore memory bank anomaly detection to capture novel, untrained track flaws.
4. **Multi-Modal Persistence Fusion & Spatial Hysteresis**:
   * Cross-modal corroboration between optical bounding boxes and accelerometer vibration spikes to suppress false positives caused by fallen leaves or ballast reflections.
5. **Universal Chainage ↔ GPS Coordinate Interpolation**:
   * Canonical linear piece-wise waypoint interpolation mapping chainage meters (`Km 3+420`) to physical GNSS coordinates along the Delhi-Agra mainline.
6. **Zero-Asset Web Audio Synthesizer**:
   * Direct Web Audio API synthesis generating dual-tone emergency sirens, high warning double-beeps, and acknowledge chimes without external audio file dependencies.

---

## 🖥️ Primary Application Routes

| Route | View | Description & Capabilities |
| :--- | :--- | :--- |
| `/` | **Operational Dashboard** | High-level command center with real-time KPI cards, signature SVG `RouteLineDiagram`, and live alerts feed. |
| `/sessions` | **Inspection Runs** | Lifecycle registry of historical and active inspection missions with distance and defect counts. |
| `/sessions/[id]` | **Inspection Viewer (Hero Screen)** | Synchronized HLS video HUD player, multi-metric telemetry waveform charts, and defect seek markers. |
| `/defects` | **Defect Registry** | High-density tabular registry with URL-synced multi-factor filters and slide-in `EvidenceDrawer`. |
| `/map` | **GIS Track Corridor** | Leaflet CartoDB Dark Matter GIS basemap with 6-tier TQI color-coded track polylines and station milestones. |
| `/alerts` | **Live Alerts Center** | Real-time SSE dispatch center with 2-tier active/history split, audio alarm synthesis, and triage escalation. |
| `/devices` | **Edge Hardware Monitoring** | Hardware diagnostics grid for Jetson/RPi nodes, remote reboot commands, and "Show Once" API key provisioning. |
| `/reports` | **RDSO Reports & Export** | Ministry of Railways / RDSO TMD v2.4 compliant CSV and Apache Parquet export workspace. |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Node.js**: `>= 18.18.0`
- **pnpm**: `>= 9.0.0` (`pnpm@11.17.0` recommended)
- **Python**: `>= 3.10` (for FastAPI backend & ML pipelines)

### 2. Installation & Workspace Setup

```bash
# Clone the repository
git clone https://github.com/Mayank8159/TrackChain.git
cd TrackChain

# Install monorepo dependencies
npx -y pnpm@11.17.0 install
```

### 3. Running the Application

```bash
# Start Next.js frontend dev server (port 3000)
npx -y pnpm@11.17.0 --filter @trackchain/app dev
```

* Open your browser to: **`http://localhost:3000`**

### 4. Monorepo Verification Commands

```bash
# Run TypeScript compilation check across all packages (0 errors)
npx -y pnpm@11.17.0 type-check

# Run production build (all 11 Next.js routes)
npx -y pnpm@11.17.0 build
```

---

## 🎯 The SIH Evaluator "Golden Path" Demo

To experience the high-stakes evaluation scenario in under 5 minutes:

1. **Start on `/` (Operational Dashboard)**: Observe the macro Delhi-Agra corridor health and TQI score.
2. **Inject Live Fault**: Click **`[⚡ Simulate Fault]`** in the dashboard header (or press **`Ctrl+Shift+D`** / **`Cmd+Shift+D`**).
3. **Hear & Observe Alarm**: The dual-tone emergency siren sounds, and a Critical IAL Twist Exceedance alert appears in the feed.
4. **Deep-Link to Inspection Hero**: Click **`[View in Session ▶]`** on the alert to auto-seek the video and telemetry playhead to the exact defect second (`t=45s`).
5. **Inspect & Triage**: Open the **Evidence Drawer**, inspect the bounding box and raw signals, and click **`[Acknowledge]`**.
6. **Verify Spatial & Compliance Flow**: View the updated state on the **GIS Map (`/map`)** and export the audit trail on **Reports (`/reports`)**.

---

## 📚 Jury Evaluation & Pitch Resources

* 📋 **[SIH Pre-Flight Demo Checklist](docs/SIH_DEMO_CHECKLIST.md)** — Display, browser, audio, and network proof setup.
* 🎙️ **[5-Minute SIH Presenter Script](docs/SIH_DEMO_SCRIPT.md)** — Verbatim minute-by-minute pitch choreography.
* 🛡️ **[Technical Jury Q&A Defense](docs/SIH_QA_DEFENSE.md)** — In-depth architectural answers for expert jury probing.
* 🏗️ **[System Architecture Reference](docs/architecture.md)** — Complete edge, backend, and frontend system design.
* 🤖 **[ML Two-Stream Design](docs/ml-design.md)** — Mathematical formulations for vision and physics feature streams.

---

## 📜 Standards & Compliance

* **RDSO TMD v2.4**: Research Design and Standards Organisation Track Management Directorate specifications.
* **EN 13848-1:2019**: Railway applications — Track — Track geometry quality parameters.
* **Indian Railways Permanent Way Manual (IRPWM)**: Chapter 6 Track Recording & Quality Tolerances.

---

<div align="center">
  <sub>Developed for Smart India Hackathon · Ministry of Railways</sub><br/>
  <sub>TrackChain Core Architecture © 2026</sub>
</div>
