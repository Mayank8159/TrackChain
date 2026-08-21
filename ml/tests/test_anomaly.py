# Unit tests for PatchCore visual anomaly detector & calibration (tc.v1 SOTA).

import pytest
import numpy as np
from pathlib import Path
from PIL import Image
import torch

from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator
from ml.training.train_anomaly import greedy_coreset_subsampling
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from ml.models.vision.patchcore_enhanced import EnhancedPatchCore
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
    assert 0.0 <= sig.calibrated_prob <= 1.0


def test_enhanced_patchcore_multiscale_pipeline(tmp_path):
    # Initialize EnhancedPatchCore with resnet18 for fast testing
    model = EnhancedPatchCore(
        backbone="resnet18",
        patch_sizes=[3, 5],
        coreset_ratio=0.10,
        dimension_reduction=True,
        target_dim=64,
        device="cpu"
    )
    
    # Create 3 synthetic sample images
    img_paths = []
    for i in range(3):
        img_arr = (np.random.rand(224, 224, 3) * 255).astype(np.uint8)
        p = tmp_path / f"norm_{i}.jpg"
        Image.fromarray(img_arr).save(p)
        img_paths.append(p)
    
    # Build multi-scale memory banks
    model.build_memory_bank(img_paths, batch_size=2)
    assert len(model.memory_banks) == 2
    assert 3 in model.memory_banks
    assert 5 in model.memory_banks
    assert model.memory_banks[3]["dimension"] == 64
    
    # Calibrate on samples
    model.calibrate(img_paths, target_fpr=0.05)
    assert "ensemble" in model.calibration_params
    assert "patch_3" in model.calibration_params
    assert "threshold" in model.calibration_params["ensemble"]
    
    # Predict multi-scale
    test_img = np.ones((224, 224, 3), dtype=np.uint8) * 120
    scores = model.predict(test_img)
    assert "patch_3" in scores
    assert "patch_5" in scores
    assert "ensemble" in scores
    
    # Predict signals
    signals = model.predict_signals(test_img)
    assert len(signals) == 1
    sig = signals[0]
    assert isinstance(sig, CalibratedSignal)
    assert sig.signal_type == SignalType.VISUAL_NOVEL
    assert sig.stream_name == "patchcore_anomaly"
    assert "multiscale_scores" in sig.metadata
    
    # Save model and reload
    save_dir = tmp_path / "enhanced_ckpt"
    model.save(save_dir)
    assert (save_dir / "config.json").exists()
    assert (save_dir / "calibration.json").exists()
    assert (save_dir / "memory_bank_3.npz").exists()
    
    loaded_model = EnhancedPatchCore(device="cpu")
    loaded_model.load(save_dir)
    assert len(loaded_model.memory_banks) == 2
    assert "ensemble" in loaded_model.calibration_params
    
    # Test PatchCoreAnomalyDetector wrapping the saved directory checkpoint
    detector = PatchCoreAnomalyDetector(backbone_name="resnet18", checkpoint_path=save_dir)
    assert detector.enhanced_model is not None
    det_signals = detector.predict(test_img)
    assert len(det_signals) == 1
    assert det_signals[0].stream_name == "patchcore_anomaly"
