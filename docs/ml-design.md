# ML design: two streams, calibration, rule fusion, and dataset mapping.

# TrackChain Machine Learning Architecture

## Dual-Stream Processing Design

### 1. Vision Stream
- **YOLOv8 Detector**: Bounding-box detection for discrete surface anomalies: cracks, missing fasteners, squats, spalling.
- **PatchCore Feature Memory Bank**: Unsupervised anomaly detection on normal railhead embeddings extracted via WideResNet-50.
- **Texture Classifier**: Spectral energy analysis & CNN for corrugation detection.

### 2. Geometry Stream
- **EN 13848-1/5 Physics Math**: Real-time evaluation of:
  - Track gauge variation ($\Delta G = G - 1435\text{ mm}$)
  - Cant / cross-level ($h_t$)
  - 3m base twist rate ($\frac{dh_t}{dx}$)
  - Vertical profile & alignment chord versine
- **Bi-LSTM Sequence Classifier**: Categorizes multi-channel geometry waveforms over 25m sliding windows into fault types.
- **Sequence VAE**: Detects novel out-of-distribution geometry patterns.

### 3. Calibration & Persistence Rule Fusion
- **Temperature Scaling**: Platt scaling to align raw classification logits with true probability.
- **FPR Operating Budget**: Sets anomaly decision threshold to maintain $\le 1\%$ false alarm rate on nominal track segments.
- **Persistence Filtering**: Requires defect detection over consecutive spatial windows before raising critical alarm.
