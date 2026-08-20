# TrackChain Machine Learning Pipeline Specification (tc.v1)

```text
Raw Video + IMU/GNSS  ──►  Distance Resampling (0.25m)  ──►  Dual-Stream ML  ──►  Calibration & Persistence Fusion  ──►  SegmentDecision (tc.v1)
```

---

## 1. Dual-Stream Architecture Overview

TrackChain combines high-frequency optical computer vision and continuous physical geometry analytics into a unified inference and calibration pipeline:

### Stream A: Vision Stream (Surface & Component Faults)
1. **YOLOv8 Defect Detector**:
   - Supervised detection of discrete components: `missing_fastener`, `damaged_fastener`, `rail_crack`, `obstruction`.
   - Emits bounding box coordinates `[x1, y1, x2, y2]`, raw classification score, and label.
2. **PatchCore Anomaly Detector**:
   - Unsupervised memory-bank surface anomaly detection on high-resolution railhead frames.
   - Detects novel defects: `spalling`, `squats`, `corrugation`, `foreign_matter`.
   - Emits patch-level anomaly score and image-level distance metric.

### Stream B: Geometry Stream (Track Dynamics & EN 13848 Standards)
1. **Deterministic EN 13848-1 Physics Calculator**:
   - Computes gauge deviation Δ, cross-level / cant (mm), 3m chord twist rate (mm/m), and chord versines.
   - Threshold checks against Alert Limit (AL) and Immediate Action Limit (IAL).
2. **Bi-LSTM Geometry Classifier**:
   - Sequence model over resampled spatial windows (50–100m) classifying dynamic fault modes (`twist_exceedance`, `gauge_widening`, `rough_track`).
3. **Sequence VAE**:
   - Deep generative autoencoder scoring reconstruction error on continuous multi-axis IMU/geometry signals to flag novel track foundation subsidence or hunting oscillations.

---

## 2. Confidence Calibration & Thresholding

Raw neural network logits are non-probabilistic and susceptible to distribution shift. TrackChain standardizes all model outputs using calibrated probabilities:

1. **Temperature Scaling**:
   $$P_{\text{cal}}(y=k \mid x) = \frac{\exp(z_k / T)}{\sum_j \exp(z_j / T)}$$
   Optimized on validation sets using negative log-likelihood (NLL).
2. **False Positive Rate (FPR) Budgeting**:
   Anomaly detector thresholds are computed empirically on verified nominal track data to guarantee an operating FPR budget:
   $$\tau = \text{Percentile}_{100 - \text{FPR}}(S_{\text{nominal}})$$

---

## 3. Persistence Rule Fusion Contract

Individual frame anomalies can be triggered by dust, motion blur, or track debris. TrackChain applies a spatial and temporal persistence rule fusion engine:

```python
@dataclass
class SegmentDecision:
    window_id: str
    start_chainage_m: float
    end_chainage_m: float
    decision: DecisionType  # OK, INSPECT_KNOWN, INSPECT_NOVEL
    confidence: float
    primary_fault: Optional[DefectClass] = None
    defect_family: DefectFamily = DefectFamily.VISUAL_COMPONENT
    severity: SeverityLevel = SeverityLevel.LOW
    signals: List[CalibratedSignal] = field(default_factory=list)
    evidence: Optional[MediaReference] = None
    timestamp: Optional[str] = None
    schema_version: str = "tc.v1"
```

### Fusion Decision Cascade:
1. If any calibrated known signal satisfies $\text{calibrated\_prob} \ge \tau_{\text{known}}$ across the spatial persistence window $\to$ `INSPECT_KNOWN`.
2. Else if any calibrated anomaly signal satisfies $\text{calibrated\_prob} \ge \tau_{\text{novel}}$ across the spatial persistence window $\to$ `INSPECT_NOVEL`.
3. Else $\to$ `OK`.
