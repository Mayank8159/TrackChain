# TrackChain — Technical Jury Q&A Defense & Architecture FAQ

This document provides deep technical answers to anticipated questions from Smart India Hackathon jury evaluators and domain experts.

---

### Q1: "How does your AI handle novel track defects it hasn't been trained on (out-of-distribution flaws)?"

**Core Defense**:
> *"We do not rely solely on supervised object detection like standard YOLO models. We employ a dual-branch hybrid detection architecture:*
> 
> 1. **Supervised Branch**: YOLOv8-Rail handles known discrete defects (transverse cracks, missing Pandrol clips, squat defects, gauge widening).
> 2. **Unsupervised Out-of-Distribution Branch**: A **Sequence Variational Autoencoder (VAE)** paired with a **PatchCore anomaly extractor** running on memory banks of nominal healthy track features. 
> 
> *When an anomalous surface texture or strange geometric oscillation occurs, the reconstruction error and Mahalanobis distance in the latent feature space exceed the 99th percentile threshold ($\mu + 3\sigma$), flagging the anomaly as an 'Unclassified Anomaly' for human triage without requiring prior training samples."*

---

### Q2: "What happens when an inspection train enters a tunnel or remote rural ghat where 4G/5G connectivity drops?"

**Core Defense**:
> *"TrackChain is strictly **Edge-First and Disconnected-Tolerant by Design**:*
> 
> 1. **Local Edge Buffering**: Each edge computing node (NVIDIA Jetson / Raspberry Pi 5) runs a local SQLite buffer with circular Write-Ahead Logging (WAL) and local NVMe storage.
> 2. **Local Inference Execution**: YOLO inference, IMU digital filtering, and EN 13848-1 geometry estimations happen 100% on-device at the sensor head, independent of network status.
> 3. **Automatic Resilient Backpressure Sync**: When network connectivity is restored upon exiting the tunnel, the edge daemon establishes a persistent WebSocket / SSE session, replaying queued telemetry packets with idempotency tokens to eliminate duplicates."*

---

### Q3: "How do you prevent false positives from flooding the control room and fatiguing inspectors?"

**Core Defense**:
> *"We implement a multi-layered **Multi-Modal Persistence & Spatial Hysteresis Fusion Filter** (`ml/fusion/rules.py`):*
> 
> 1. **Cross-Modal Corroboration**: A visual crack flag is only elevated to 'Critical' if the corresponding IMU accelerometer detects an RMS vibration spike ($> 2.2g$) within a $\pm 1.5\text{m}$ spatial window.
> 2. **Temporal Window Persistence**: Discrete frame anomalies must persist across at least 3 consecutive video frames or consecutive axle passes to eliminate transient ballast reflections or fallen leaves.
> 3. **Spatial Hysteresis**: Re-detecting a known minor defect within 5 meters suppresses duplicate alarm bells and instead updates the historical degradation rate in the database."*

---

### Q4: "Is TrackChain just a standalone web dashboard, or can it integrate into existing Indian Railways enterprise IT?"

**Core Defense**:
> *"TrackChain is built directly against **Indian Railways & RDSO Specifications**:*
> 
> 1. **RDSO TMD v2.4 Compliance**: We export inspection data into the exact CSV and Apache Parquet schema required by the Track Management Directorate (TMD).
> 2. **REST & SSE OpenAPI Endpoints**: Our FastAPI backend exposes standard OpenAPI 3.0 REST and Server-Sent Event endpoints, allowing direct ingestion into Indian Railways TMS (Track Management System) and COA (Control Office Application).
> 3. **SCADA Integration**: Telemetry payloads adhere to IEC 60870-5-104 and OPC UA protocol mappings for high-voltage and interlocking control integration."*

---

### Q5: "How do you ensure the telemetry and defect audit trail cannot be tampered with or repudiated?"

**Core Defense**:
> *"Every sensor frame and defect inference payload includes a **Cryptographic Edge Integrity Chain**:*
> 
> 1. **Hardware-Signed Telemetry**: Edge nodes sign every 1-second telemetry batch with a SHA-256 HMAC generated using a hardware-isolated device key (`tc_live_sec_...`) provisioned in the TPM / secure enclave.
> 2. **Immutable Chain of Custody**: When an operator acknowledges or rejects a defect, the action is logged with an IST timestamp, the operator ID, and a cryptographic hash of the raw sensor frame. This prevents retroactive falsification of safety logs during RDSO statutory inquiries."*
