# ML package overview: two-stream design, calibration, and rule fusion.

# TrackChain ML Package

Edge-native dual-stream machine learning pipeline for real-time track condition assessment and defect classification.

---

## 🔬 Architecture

```
                 ┌────────────────────────────────┐
                 │      Edge Sensor Ingestion     │
                 │   (Camera, IMU, Laser, GNSS)   │
                 └───────────────┬────────────────┘
                                 │
                 ┌───────────────┴────────────────┐
                 │ Resample to Distance Chainage │
                 │      (ml.core.chainage)        │
                 └───────┬────────────────┬───────┘
                         │                │
            ┌────────────▼───┐        ┌───▼────────────┐
            │  Vision Stream │        │ Geometry Stream│
            │  - YOLOv8 (det)│        │ - EN 13848 math│
            │  - PatchCore   │        │ - Bi-LSTM type │
            │    (anomaly)   │        │ - Seq VAE      │
            └────────────┬───┘        └───┬────────────┘
                         │                │
                         └────────┬───────┘
                                  ▼
                     ┌────────────────────────┐
                     │ Temperature Scaling &  │
                     │  FPR Calibration       │
                     └────────────┬───────────┘
                                  ▼
                     ┌────────────────────────┐
                     │ Persistence Rule Fusion│
                     │ (OK / KNOWN / NOVEL)   │
                     └────────────────────────┘
```

1. **Vision Stream**:
   - **YOLOv8 Object Detector**: Detects known discrete surface anomalies (cracks, missing fasteners, squats, spalling).
   - **PatchCore Feature Memory**: Unsupervised normal-only feature bank detecting novel or rare railhead anomalies.
   - **Texture Classifier**: Spectral and CNN classifier for corrugation patterns.

2. **Geometry Stream**:
   - **EN 13848 Deterministic Physics Features**: Twist rate ($mm/m$), cross-level ($cant$), alignment versine, and vertical unevenness.
   - **Bi-LSTM Fault Classifier**: Sequence model classifying multi-channel geometry waveforms into defect classes.
   - **Sequence VAE**: Autoencoder trained exclusively on nominal track geometry to detect novel dynamics.

3. **Calibration & Fusion**:
   - **Temperature / Platt Scaling**: Calibrates raw network logits to true posterior probabilities.
   - **FPR Operating Budgeting**: Sets anomaly thresholds to satisfy strict false-positive rate constraints.
   - **Rule-Based Persistence Fusion**: Aggregates vision and geometry signals over sliding spatial windows with persistence filtering.
