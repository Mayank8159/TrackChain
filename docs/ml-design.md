# TrackChain Multi-Modal Machine Learning Architecture Specification (tc.v1)

```text
Raw Video + IMU/GNSS  ──►  Distance Resampling (0.25m)  ──►  5-Model AI Pipeline  ──►  Master Fusion Engine  ──►  SegmentDecision (tc.v1)
```

---

## 1. Multi-Modal Pipeline Overview

TrackChain combines high-frequency computer vision, deterministic railway physics, deep recurrent sequence classification, and generative anomaly detection into a synchronized edge inference pipeline:

```text
                               ┌──► YOLOv8n (Known Vision)          ──► CalibratedSignal (VISUAL_KNOWN)
                               ├──► PatchCore (Novel Vision)        ──► CalibratedSignal (VISUAL_NOVEL)
TrackSegment (0.25m bins) ────┼──► EN 13848 Physics (Deterministic)──► CalibratedSignal (GEOMETRY_KNOWN)
                               ├──► Bi-LSTM + Attention (Classifier)──► CalibratedSignal (GEOMETRY_KNOWN_TYPE)
                               └──► Sequence VAE (Novel Geometry)   ──► CalibratedSignal (GEOMETRY_NOVEL)
                                                                               │
                                                                               ▼
                                                                     [Master Fusion Engine]
                                                                               │
                                                                               ▼
                                                                        SegmentDecision
```

---

## 2. The 5 Inference Models

### 1. YOLOv8n Rail Defect Detector (Supervised Vision)
- **Defects Covered**: `missing_fastener`, `damaged_fastener`, `rail_crack`, `obstruction`.
- **Optimization**: Slicing Aided Hyper Inference (SAHI) for millimeter-scale defect detection on high-resolution frames.
- **Export Formats**: ONNX FP32 and INT8 Dynamic Quantization for Raspberry Pi 5 / Jetson.
- **Calibration**: Temperature Scaling ($T$).

### 2. PatchCore Railhead Anomaly Detector (Unsupervised Vision)
- **Defects Covered**: `spalling`, `squats`, `corrugation`, `surface_burns`, `foreign_matter`.
- **Memory Bank**: 2,508 representative normal patch embeddings selected via greedy core-set subsampling from a `WideResNet50_2` feature space.
- **Search Engine**: Fast $L_2$ nearest-neighbor search via `faiss.IndexFlatL2`.
- **Calibration**: Sigmoid Extreme Value Theory ($P_{99} = 13.68, k = 0.50$).

### 3. Vectorized EN 13848 & RDSO Track Geometry Physics (Deterministic)
- **Math Engine**: Vectorized multi-chord algorithm executing in $<1\text{ ms}$ over 1,000m.
- **Parameters Calculated**:
  - Cross-Level / Cant: $C(x) = 1676.0 \cdot \sin(\text{Roll}(x))$
  - Multi-Base Twist: 3m base and 6m base twist rates
  - Mid-Chord Versine: 10m and 20m chord lateral alignments
  - Longitudinal Level (Unevenness): 10m and 30m vertical chord profiles
  - Track Quality Index (TQI): Composite standard deviation penalty index
- **Calibration**: Normalized Exceedance Ratio ($\text{Measured} / (2 \times \text{Limit})$).

### 4. Bi-LSTM + Attention Geometry Fault Classifier (Deep Sequence)
- **Architecture**: 2-layer Bidirectional LSTM with multi-head spatial self-attention over 20m windows (80 spatial bins).
- **Fault Classes**: `twist_fault`, `gauge_fault`, `alignment_fault`, `unevenness_fault`.
- **Attention Mechanism**: Pinpoints the exact spatial bin causing the sequence exceedance for visual explainability.
- **Calibration**: Temperature Scaling ($T$).

### 5. Dilated 1D-CNN Sequence VAE (Generative Geometry Anomaly)
- **Architecture**: Dilated 1D-CNN encoder and decoder with residual connections over multi-axis IMU/geometry signals.
- **Dual-Path Anomaly Scoring**:
  $$\text{Score} = w_{\text{recon}} \cdot \text{MSE}(\mathbf{x}, \hat{\mathbf{x}}) + w_{\text{latent}} \cdot D_M(\mathbf{z}, \boldsymbol{\mu}_0, \boldsymbol{\Sigma}_0)$$
  - Path 1: Reconstruction Error (catches structural pattern deviations).
  - Path 2: Latent Mahalanobis Distance (catches out-of-distribution latent representations).
- **Calibration**: Sigmoid EVT calibration ($P_{99}$).

---

## 3. Master Fusion Engine Mechanics

1. **Confidence-Weighted Fusion**: Weighs model contributions dynamically based on modality confidence.
2. **Cross-Modal Correlation Boost**: When visual defects and geometry faults coincide at the same chainage, severity is automatically elevated to `CRITICAL`.
3. **Exponential Hysteresis**:
   $$h_t = \alpha \cdot s_t + (1 - \alpha) \cdot h_{t-1}$$
   Suppresses transient single-frame spikes while maintaining continuity across sustained defects.
4. **Adaptive Section Thresholds**: Automatically adjusts detection sensitivity when transitioning between straight high-speed tangent track, curved territory, and switch/turnout zones.
