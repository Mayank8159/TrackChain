# Unit tests for PatchCore visual anomaly detector & calibration (tc.v1 SOTA).

import pytest
import numpy as np
from pathlib import Path
from PIL import Image

from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator
from ml.training.train_anomaly import greedy_coreset_subsampling
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from ml.core.schema import DefectClass, SignalType, CalibratedSignal


def test_sigmoid_calibrator_fit_and_scale(tmp_path):
    # Baseline normal distances
    normal_dists = np.linspace(1.0, 10.0, 100)
    calibrator = SigmoidDistanceCalibrator(steepness_k=0.5, percentile=99.0)

    p99 = calibrator.fit(normal_dists)
    assert p99 > 9.0
    assert calibrator.is_fitted

    # Score at exact threshold should be 0.50 (50%)
    score_at_t = calibrator.scale(p99)
    assert abs(score_at_t - 0.50) < 1e-4

    # Low distance should be near 0.0
    low_score = calibrator.scale(1.0)
    assert low_score < 0.05

    # High anomaly distance should be near 1.0
    high_score = calibrator.scale(p99 + 15.0)
    assert high_score > 0.99

    # Test serialization
    json_path = tmp_path / "patchcore_calib.json"
    calibrator.save(json_path)
    assert json_path.exists()

    loaded = SigmoidDistanceCalibrator.load(json_path)
    assert abs(loaded.threshold - p99) < 1e-4
    assert loaded.is_fitted


def test_greedy_coreset_subsampling():
    np.random.seed(42)
    features = np.random.randn(200, 64).astype(np.float32)
    
    # 10% coreset ratio
    coreset = greedy_coreset_subsampling(features, sampling_ratio=0.10)
    assert coreset.shape[0] == 20
    assert coreset.shape[1] == 64


def test_patchcore_heatmap_bounding_box_extraction():
    detector = PatchCoreAnomalyDetector(backbone_name="resnet18")
    
    # Create synthetic 2D heatmap with high anomaly hotspot at (100, 100)
    heatmap = np.zeros((200, 200), dtype=np.float32)
    heatmap[80:120, 80:120] = 50.0  # Hotspot box
    
    bbox = detector.extract_bounding_box(heatmap, threshold=0.50)
    assert bbox is not None
    x1, y1, x2, y2 = bbox
    assert x1 <= 90
    assert y1 <= 90
    assert x2 >= 110
    assert y2 >= 110


def test_patchcore_predict_with_memory_bank():
    detector = PatchCoreAnomalyDetector(backbone_name="resnet18")
    
    # Create synthetic image
    img = np.ones((224, 224, 3), dtype=np.uint8) * 128
    
    # Extract features to determine dimension
    import torch
    tensor = detector.transform(Image.fromarray(img)).unsqueeze(0)
    with torch.no_grad():
        feats, _ = detector.extract_features(tensor)
    
    feat_dim = feats.shape[1]
    
    # Set a normal memory bank using these features
    normal_bank = feats.cpu().numpy().astype(np.float32)
    detector.set_memory_bank(normal_bank)
    
    # Calibrate
    detector.calibrator.fit([1.0, 2.0, 3.0])
    
    # Run prediction on identical image -> distance should be near 0
    signals = detector.predict(img)
    assert len(signals) == 1
    sig = signals[0]
    
    assert isinstance(sig, CalibratedSignal)
    assert sig.signal_type == SignalType.VISUAL_NOVEL
    assert sig.predicted_class == DefectClass.VISUAL_ANOMALY
    assert sig.stream_name == "patchcore_anomaly"
    assert sig.calibrated_prob >= 0.0 and sig.calibrated_prob <= 1.0
