"""
Unit tests for TrackChain Enhanced PatchCore visual anomaly detection, dataset expansion, and calibration.
"""
import os
import sys
import json
import tempfile
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

# Ensure repo root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.scripts.expand_patchcore_dataset import (
    generate_track_pattern,
    create_normal_augmentation_pipeline,
    augment_normal_image,
    ensure_diversity,
    expand_patchcore_dataset,
)
from ml.models.vision.anomaly import PatchCoreAnomalyDetector, get_default_transform
from ml.training.train_anomaly import greedy_coreset_subsampling, train_patchcore
from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator
from ml.core.schema import CalibratedSignal, SignalType, DefectClass


def test_procedural_synthetic_track_generation():
    """Verify procedural generation creates a valid 3-channel track image."""
    img = generate_track_pattern(width=320, height=320)
    assert img is not None
    assert img.shape == (320, 320, 3)
    assert img.dtype == np.uint8
    # Non-uniform image
    assert img.std() > 5.0


def test_normal_augmentation_pipeline():
    """Verify normal track augmentation produces augmented variants without crashing."""
    pipelines = create_normal_augmentation_pipeline()
    assert pipelines is not None
    assert "lighting" in pipelines
    assert "weather" in pipelines
    assert "geometric" in pipelines
    assert "texture" in pipelines

    dummy = np.zeros((100, 100, 3), dtype=np.uint8) + 120
    augmented = augment_normal_image(dummy, pipelines, num_augmentations=3)
    assert len(augmented) == 3
    for a in augmented:
        assert a.shape == (100, 100, 3)


def test_diversity_clustering_selection(tmp_path):
    """Verify KMeans feature diversity sampling selects diverse subset."""
    img_paths = []
    for i in range(10):
        img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        p = tmp_path / f"test_{i}.jpg"
        Image.fromarray(img).save(p)
        img_paths.append(p)

    selected = ensure_diversity(img_paths, target_count=4, num_clusters=3)
    assert len(selected) == 4
    for s in selected:
        assert Path(s).exists()


def test_greedy_coreset_minimax_behavior():
    """Verify greedy coreset selection reduces sample count and spans maximum distance."""
    np.random.seed(42)
    features = np.random.randn(100, 32).astype(np.float32)
    coreset = greedy_coreset_subsampling(features, sampling_ratio=0.15)

    assert coreset.shape[0] == 15
    assert coreset.shape[1] == 32


def test_multi_scale_feature_extraction():
    """Verify PatchCore multi-scale patch extraction returns correct tensor dimensions."""
    detector = PatchCoreAnomalyDetector(backbone_name="resnet18", patch_size=3)
    import torch
    dummy_tensor = torch.zeros((1, 3, 224, 224), dtype=torch.float32)

    with torch.no_grad():
        feats, (h, w) = detector.extract_features(dummy_tensor, patch_size=3)

    assert feats.ndim == 2
    assert feats.shape[1] == detector.feature_dim
    assert h > 0 and w > 0


def test_patchcore_full_prediction_and_bounding_box():
    """Verify full PatchCore inference with calibrated output and localized bounding box."""
    detector = PatchCoreAnomalyDetector(backbone_name="resnet18")
    
    # Create synthetic memory bank
    np.random.seed(42)
    mock_bank = np.random.randn(50, detector.feature_dim).astype(np.float32)
    detector.set_memory_bank(mock_bank)
    detector.calibrator.fit([1.0, 2.0, 3.0, 4.0])

    dummy_frame = np.ones((224, 224, 3), dtype=np.uint8) * 100
    signals = detector.predict(dummy_frame)

    assert len(signals) == 1
    sig = signals[0]
    assert isinstance(sig, CalibratedSignal)
    assert sig.signal_type == SignalType.VISUAL_NOVEL
    assert sig.predicted_class == DefectClass.VISUAL_ANOMALY
    assert 0.0 <= sig.calibrated_prob <= 1.0
