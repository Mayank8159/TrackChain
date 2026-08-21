# TrackChain Machine Learning Intelligence Stack (`tc.v1`)

> Edge-native multi-modal intelligence stack combining Computer Vision, High-Precision Spatial Geometry Physics, Attention Sequence Modeling, and Rule-Based Persistence Fusion for railway infrastructure safety.

---

## 📑 Table of Contents

1. [Architectural Overview](#-architectural-overview)
2. [The 5-Model Triad & Novelty Matrix](#-the-5-model-triad--novelty-matrix)
3. [Physical Feature Engineering & Standards](#-physical-feature-engineering--standards)
4. [Deep Learning Model Architecture](#-deep-learning-model-architecture)
5. [Master Rule-Based Fusion Engine](#-master-rule-based-fusion-engine)
6. [Post-Processing Calibration Framework](#-post-processing-calibration-framework)
7. [Universal Signal & Schema Contract](#-universal-signal--schema-contract)
8. [Data Inventory & Synthesis](#-data-inventory--synthesis)
9. [Training, Calibration & Testing Runbook](#-training-calibration--testing-runbook)
10. [Edge Quantization & Hardware Deployment](#-edge-quantization--hardware-deployment)

---

## 🔬 Architectural Overview

TrackChain operates as a **synchronized dual-stream edge pipeline**. Incoming sensors (High-Speed RGB Cameras, 100Hz IMU accelerometers/gyroscopes, and Optical Laser Gauge Profilers) are resampled from the time domain onto a strict **spatial distance chainage grid ($\Delta x = 0.25$m)**.

```mermaid
flowchart TD
    subgraph INGESTION ["📡 Multi-Modal Sensor Ingestion"]
        A1[High-Speed RGB Cameras<br/>60 FPS 1080p]
        A2[3-Axis IMU Telemetry<br/>100 Hz Accelerometer / Gyro]
        A3[Optical Laser Profiler<br/>Gauge / Rail Profile]
        A4[High-Precision GNSS<br/>Coordinates & Track Chainage]
    end

    subgraph RESAMPLING ["📏 Spatial Chainage Resampler (ml.core.chainage)"]
        B[Equidistant Spatial Binning<br/>Δx = 0.25m | 20m Spatial Segments]
    end

    A1 --> B
    A2 --> B
    A3 --> B
    A4 --> B

    subgraph VISION_STREAM ["👁️ Vision Stream"]
        V1["Phase 2.1: YOLOv8n Detector<br/>(VISUAL_KNOWN: Fasteners, Cracks)"]
        V2["Phase 2.2: PatchCore Anomaly<br/>(VISUAL_NOVEL: Surface Defects)"]
    end

    subgraph GEOMETRY_STREAM ["📐 Geometry Stream"]
        G1["Phase 2.3: EN 13848 Physics<br/>(GEOMETRY_KNOWN: Twist, Gauge, Cant)"]
        G2{"Physics Limit<br/>Exceeded?"}
        G3["Phase 2.4: Bi-LSTM Attention<br/>(GEOMETRY_KNOWN_TYPE: Dipped Joint, etc.)"]
        G4["Phase 2.5: 1D-CNN Sequence VAE<br/>(GEOMETRY_NOVEL: Resonance, Voids)"]
    end

    B --> VISION_STREAM
    B --> GEOMETRY_STREAM

    G1 --> G2
    G2 -- YES --> G3
    G2 -- NO --> G4

    subgraph CALIBRATION ["🎯 Unified Calibration Layer (ml.calibration)"]
        C1[Platt Temperature Scaling]
        C2[Sigmoid P99 Distance Scaling]
        C3[Deterministic Exceedance Ratio]
    end

    V1 --> C1
    V2 --> C2
    G1 --> C3
    G3 --> C1
    G4 --> C2

    subgraph FUSION_ENGINE ["🧠 Master Persistence Rule Fusion (ml.fusion)"]
        F1[Confidence-Weighted Voting Matrix]
        F2[Cross-Modal Correlation Boost: 1.5x]
        F3[Exponential Decay Spatial Hysteresis]
        F4[Adaptive Section Criticality Routing]
    end

    C1 --> FUSION_ENGINE
    C2 --> FUSION_ENGINE
    C3 --> FUSION_ENGINE

    subgraph OUTPUT ["🚀 Operational Output (tc.v1)"]
        OUT["SegmentDecision (OK / INSPECT_KNOWN / INSPECT_NOVEL)<br/>+ ExplainabilityTrace & MediaReference"]
    end

    FUSION_ENGINE --> OUTPUT
```

---

## 🧩 The 5-Model Triad & Novelty Matrix

| Stream | Phase | Model | Domain | Target Defects | Execution Policy |
|---|---|---|---|---|---|
| **Vision Known** | **2.1** | **YOLOv8n** | Discrete visual defects | Missing fastener clip, railhead crack, broken sleeper | Always active on every camera frame |
| **Vision Novel** | **2.2** | **PatchCore** | Unsupervised surface novelty | Ballast contamination, unexpected rail burn, spalling | Always active; memory bank distance evaluated |
| **Geometry Known** | **2.3** | **EN 13848 Physics** | Deterministic limit exceedance | 3m Twist $> 4$mm, Gauge Widening $> 6$mm, Unevenness | Always active; 0ms vector math over 20m window |
| **Geometry Type** | **2.4** | **Bi-LSTM Attention** | Sequential fault morphology typing | Dipped joint, cyclic top, cant transition, lateral kink | **Conditional** (Runs only when Phase 2.3 detects exceedance) |
| **Geometry Novel** | **2.5** | **1D-CNN Seq-VAE** | Unsupervised dynamic resonance | Subgrade void, harmonic track sway, structural settling | Always active on micro-geometry |

---

## 📐 Physical Feature Engineering & Standards

All track calculations strictly conform to **EN 13848-1/2** and **RDSO Track Recording Standards**:

### 1. Multi-Chord Filtering Formulae
- **Cross-Level (Cant)**:
  $$ \text{Cant (mm)} = G \cdot \sin(\theta_{\text{roll}}) \approx G \cdot \theta_{\text{roll}} \quad (G = 1676\text{mm}) $$
- **RDSO 3-Meter Twist Rate**:
  $$ \text{Twist}_{3\text{m}} = |\text{Cant}(x) - \text{Cant}(x - 3.0\text{m})| $$
- **Multi-Chord Versine ($L = 10\text{m}, 20\text{m}$)**:
  $$ V_L(x) = y(x) - \frac{y(x - L/2) + y(x + L/2)}{2} $$
- **Track Quality Index (TQI)**:
  $$ \text{TQI} = \sum_{i=1}^5 \sigma_i \quad (\text{Sum of standard deviations across unevenness, twist, alignment, gauge, cant}) $$

---

## 🤖 Deep Learning Model Architecture

### 1. Bi-LSTM with Spatial Attention (Phase 2.4)
- **Input**: $(B, 80, 5)$ representing an 80-bin (20m) window across 5 EN 13848 features.
- **Backbone**: `LayerNorm(5)` $\to$ 2-layer Bidirectional LSTM ($H=64$, bidirectional size $= 128$).
- **Temporal Attention**: Computes spatial attention weights $\alpha \in \mathbb{R}^{B \times 80}$ highlighting the exact 0.25m bin responsible for the exceedance.

### 2. 1D-CNN Dilated Sequence VAE (Phase 2.5)
- **Multi-Scale Dilated Encoder**:
  - Branch Short: `Conv1d(5, 32, dilation=1)` (1–3m short wavelengths)
  - Branch Medium: `Conv1d(5, 32, dilation=4)` (3–10m medium wavelengths)
  - Branch Long: `Conv1d(5, 32, dilation=10)` (10–30m long wavelengths)
- **Bottleneck**: 16-dimensional latent space with $\beta$-VAE loss ($\beta = 0.01$) prioritizing reconstruction fidelity.
- **Dual-Path Anomaly Scoring**:
  $$ \text{Score} = 0.7 \cdot \text{MSE}_{\text{recon}} + 0.3 \cdot D_{\text{mahal}}(\mu_{\text{test}}, \mu_{\text{norm}}, \Sigma_{\text{norm}}^{-1}) $$

---

## 🧠 Master Rule-Based Fusion Engine

The `TrackChainFusionEngine` integrates multi-modal signals using deterministic safety logic:

1. **Immediate Action on Known Faults**:
   - Limit breaches from Physics or discrete YOLO detections trigger instant `INSPECT_KNOWN` decisions with maintenance action routing.
2. **Cross-Modal Correlation Boost**:
   - When vision and geometry corroborate the same defect location (e.g. missing fastener causing localized twist), a **$1.5\times$ boost multiplier** elevates severity (`MEDIUM` $\to$ `HIGH` / `HIGH` $\to$ `CRITICAL`).
3. **Exponential Decay Spatial Hysteresis**:
   - Evidence accumulation across consecutive spatial windows ($S_t = 0.7 \cdot S_{t-1} + 0.3 \cdot \text{conf}$) suppresses transient noise while preserving multi-segment defect continuity.
4. **Adaptive Section Profiles**:
   - Dynamically shifts operating thresholds depending on track criticality ($0.40$ on high-speed mainline vs $0.70$ on yard tracks).

---

## 🎯 Post-Processing Calibration Framework

All models map raw outputs to calibrated probabilities in $[0.0, 1.0]$ where **$0.50$ is the universal threshold**:

| Model | Calibration Method | Formula | Parameter Storage |
|---|---|---|---|
| **YOLO** | Platt Temperature Scaling | $P = \sigma(\text{logit} / T)$ | `artifacts/calibration/yolo_temp.json` |
| **PatchCore** | Sigmoid Distance Scaling | $P = \frac{1}{1 + \exp(-k(d - P_{99}))}$ | `artifacts/calibration/patchcore_calibration.json` |
| **Physics** | Deterministic Ratio | $P = \min(1.0, \frac{\text{val}}{2 \cdot \text{limit}})$ | Hardcoded in `EN13848PhysicsThresholdDetector` |
| **Bi-LSTM** | Platt Temperature Scaling | $P = \text{Softmax}(\text{logits} / T)$ | `artifacts/calibration/bilstm_temp.json` |
| **Seq-VAE** | Sigmoid Anomaly Scaling | $P = \frac{1}{1 + \exp(-k(\text{score} - P_{99}))}$ | `artifacts/calibration/vae_calibration.json` |

---

## 📜 Universal Signal & Schema Contract

Every model emits a `tc.v1` compliant `CalibratedSignal`:

```python
@dataclass
class CalibratedSignal:
    name: str                    # e.g., "yolo_visual_detector"
    model_version: str           # e.g., "0.1.0"
    signal_type: SignalType      # VISUAL_KNOWN, VISUAL_NOVEL, GEOMETRY_KNOWN, etc.
    value: float                 # Calibrated probability [0.0, 1.0]
    raw_score: float             # Pre-calibration score
    threshold: float             # Operating threshold (0.50)
    fired: bool                  # value >= threshold
    label: DefectClass           # Defect class enum
    bbox: Optional[Tuple[float]] # Bounding box [x1, y1, x2, y2]
    explanation: Optional[Dict]  # Explainability metadata
    metadata: Dict[str, Any]     # Model details, attention peak, etc.
```

---

## 📦 Data Inventory & Synthesis

| Dataset | Purpose | Location | Count / Dimension |
|---|---|---|---|
| **Rail Defects YOLO** | Object Detection | `data/external/rail_defects/` | $>1,000$ labeled images |
| **Rail Normal PatchCore** | Anomaly Memory Bank | `data/external/rail_normal_only/` | $>500$ nominal surface images |
| **Synthetic Rail Defects** | Defect Generation (Canvas Inpainting/Overlay) | `data/external/rail_defects_synthetic/` | $>1,200$ synthesized images |
| **Synthetic TRC Telemetry** | Physics Resampling | `data/processed/synthetic_trc_run_001.csv` | 1,000m @ 100Hz |
| **5-Class Geometry Data** | Bi-LSTM Training | `data/processed/geometry_sequences/` | 5,000 sequences (CSV & NPZ) |
| **Normal Geometry Data** | Seq-VAE Training | `data/processed/normal_sequences/` | 3,000 sequences (CSV) |

---

## 🎨 Synthetic Defect Generation & SAHI Multiplier

Since real defect photos are limited, TrackChain provides high-fidelity **copy-paste and inpainting defect synthesis** using the clean normal-track image bank as canvas:

```bash
# 1. Synthesize domain-accurate defects on normal track images (cracks, missing fasteners, defective clips, obstructions)
python ml/scripts/generate_synthetic_defects.py \
    --normal-bank data/external/rail_normal_only \
    --output-dir data/external/rail_defects_synthetic \
    --samples-per-class 300 \
    --imgsz 960

# 2. (Optional) Run SAHI overlapping slicing multiplier on high-res dataset
python ml/scripts/slice_sahi_dataset.py \
    --input-dir data/external/rail_defects_synthetic \
    --output-dir data/external/rail_defects_sahi_sliced \
    --slice-size 480 \
    --overlap-ratio 0.20
```

---

## 🚀 Training, Calibration & Testing Runbook

Execute the automated pipeline from the repository root:

```bash
# 1. Master Training Orchestration (Dependency Order + Checkpointing + Upgraded YOLO Recipe)
./ml/scripts/run.sh --epochs-yolo 80 --imgsz 960 --batch 8

# 2. Standalone Upgraded YOLOv8 Detector Training
python ml/scripts/train_detector.py \
    --data data/external/rail_defects_synthetic/data.yaml \
    --config ml/configs/detector.yaml \
    --epochs 80 \
    --batch 8 \
    --imgsz 960 \
    --freeze 10 \
    --dropout 0.1 \
    --erasing 0.2 \
    --copy-paste 0.5 \
    --close-mosaic 10 \
    --patience 20 \
    --conf 0.25

# 3. Comprehensive Test-Split Validation (conf=0.25)
python ml/scripts/validate_yolo.py \
    --model artifacts/checkpoints/vision/yolov8n_rail_best.pt \
    --data data/external/rail_defects_synthetic/data.yaml \
    --conf 0.25 \
    --imgsz 960

# 4. Master Calibration Sync (Fits Temperature & Sigmoid Thresholds)
./ml/scripts/calibrate.sh

# 5. Comprehensive Test Suite Runner (All 21 Test Modules)
./ml/scripts/test.sh

# 6. Generate Formal Phase 2 Completion Report
python ml/scripts/evaluate.py --phase 2 --output docs/phase2_completion_report.md
```

---

## ⚡ Edge Quantization & Hardware Deployment

Convert PyTorch checkpoints to optimized edge runtimes:

```bash
# Export YOLOv8 to high-performance ONNX
python ml/inference/exporters.py --model artifacts/checkpoints/vision/yolov8n_rail_best.pt --format onnx

# Apply dynamic INT8 quantization for edge CPU execution (Raspberry Pi 5 / Jetson Orin Nano)
python ml/inference/exporters.py --model artifacts/checkpoints/vision/yolov8n_rail_best.pt --format int8
```

---

## 🧪 Test Verification Suite

The entire ML stack is covered by **21 specialized pytest suites (63 unit and integration tests)**:

```bash
python -m pytest ml/tests -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.1.1
rootdir: D:\TrackChain\ml
collected 63 items

ml/tests/test_adaptive_thresholds.py ...................... [PASSED]
ml/tests/test_anomaly.py .................................. [PASSED]
ml/tests/test_calibration.py .............................. [PASSED]
ml/tests/test_calibration_sync.py ......................... [PASSED]
ml/tests/test_chainage.py ................................. [PASSED]
ml/tests/test_confidence_fusion.py ........................ [PASSED]
ml/tests/test_cross_modal_boost.py ........................ [PASSED]
ml/tests/test_detector.py ................................. [PASSED]
ml/tests/test_dilated_encoder.py .......................... [PASSED]
ml/tests/test_en13848.py .................................. [PASSED]
ml/tests/test_fault_classifier.py ......................... [PASSED]
ml/tests/test_fusion.py ................................... [PASSED]
ml/tests/test_hysteresis.py ............................... [PASSED]
ml/tests/test_integration_sync.py ......................... [PASSED]
ml/tests/test_overlapping_windows.py ...................... [PASSED]
ml/tests/test_physics_detector.py ......................... [PASSED]
ml/tests/test_pipeline_integration.py ..................... [PASSED]
ml/tests/test_sequence_vae.py ............................. [PASSED]
ml/tests/test_sequence_vae_dual_path.py ................... [PASSED]
ml/tests/test_signal_contract.py .......................... [PASSED]
ml/tests/test_triad_integration.py ........................ [PASSED]

============================= 63 passed in 21.27s (100%) =============================
```
