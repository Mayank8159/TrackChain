"""
Unit tests for TrackChain custom YOLO training, dataset expansion, validation, and calibration pipeline.
"""
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
import numpy as np
import pytest
import yaml

# Ensure repo root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.scripts.expand_datasets import (
    sanitize_bbox,
    create_railway_augmentation_pipeline,
    augment_sample,
    expand_dataset,
    CLASS_MAPPING,
    CLASS_NAMES
)
from ml.scripts.train_detector import (
    resolve_device,
    MetricsLogger,
    ProgressiveTrainer
)
from ml.scripts.calibrate_yolo import calibrate_yolo


def test_sanitize_bbox_clamping_and_bounds():
    """Verify that bounding boxes are clamped, filtered for non-degeneracy, and bounded in [0, 1]."""
    # Valid box
    valid = sanitize_bbox([0.5, 0.5, 0.2, 0.2])
    assert valid is not None
    assert len(valid) == 4
    assert 0.0 < valid[0] < 1.0
    assert 0.0 < valid[1] < 1.0

    # Out of bounds box - clamped properly
    oob = sanitize_bbox([1.2, -0.5, 0.8, 0.8])
    assert oob is not None
    assert oob[0] <= 1.0 and oob[1] >= 0.0

    # Degenerate zero-size box - filtered out
    degenerate = sanitize_bbox([0.5, 0.5, 0.001, 0.001])
    assert degenerate is None


def test_railway_augmentation_pipeline_execution():
    """Verify that the multi-level railway augmentation pipeline creates valid augmented samples."""
    pipelines = create_railway_augmentation_pipeline()
    assert pipelines is not None
    assert 'basic' in pipelines
    assert 'lighting' in pipelines
    assert 'weather' in pipelines
    assert 'motion' in pipelines
    assert 'geometric' in pipelines
    assert 'occlusion' in pipelines

    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    dummy_bboxes = [{'class_id': 0, 'bbox': [0.5, 0.5, 0.2, 0.2]}]

    aug_img, aug_boxes = augment_sample(dummy_img, dummy_bboxes, pipelines)
    assert aug_img is not None
    assert aug_img.shape == (100, 100, 3)
    assert len(aug_boxes) >= 1
    assert aug_boxes[0]['class_id'] == 0


def test_expand_dataset_minimal_run():
    """Test expand_dataset function on the repository's base dataset to create valid data.yaml and splits."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_output = Path(tmp_dir) / "expanded"
        source_data = Path("data/external/rail_defects")

        if not source_data.exists():
            pytest.skip("Base dataset not present")

        result = expand_dataset(
            original_data_root=source_data,
            output_root=tmp_output,
            target_per_class=4,
            augment_factor=2,
            random_seed=123
        )

        assert 'train' in result
        assert 'valid' in result
        assert 'test' in result
        assert (tmp_output / 'data.yaml').exists()

        with open(tmp_output / 'data.yaml', 'r', encoding='utf-8') as f:
            dy = yaml.safe_load(f)
            assert dy['nc'] == 4
            assert dy['names'] == CLASS_NAMES


def test_progressive_trainer_schedule():
    """Verify progressive resolution schedule across epochs."""
    trainer = ProgressiveTrainer(base_imgsz=416, final_imgsz=640)

    # First 30% -> base resolution 416
    assert trainer.get_imgsz_for_epoch(1, 100) == 416
    assert trainer.get_imgsz_for_epoch(25, 100) == 416

    # 30% - 70% -> interpolates between 416 and 640 (multiples of 32)
    mid_res = trainer.get_imgsz_for_epoch(50, 100)
    assert 416 <= mid_res <= 640
    assert mid_res % 32 == 0

    # Last 30% -> 640
    assert trainer.get_imgsz_for_epoch(75, 100) == 640
    assert trainer.get_imgsz_for_epoch(100, 100) == 640


def test_metrics_logger_callback():
    """Verify that MetricsLogger captures epoch statistics and persists JSON."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_dir = Path(tmp_dir) / "logs"
        logger = MetricsLogger(log_dir)

        class DummyTrainer:
            epoch = 0
            loss = np.array(0.45)
            metrics = {
                'metrics/mAP50(B)': 0.72,
                'metrics/mAP50-95(B)': 0.51,
                'metrics/precision(B)': 0.85,
                'metrics/recall(B)': 0.78,
                'val/loss': 0.38,
            }
            optimizer = type('Opt', (), {'param_groups': [{'lr': 0.0008}]})()

        logger.on_fit_epoch_end(DummyTrainer())

        assert (log_dir / 'training_metrics.json').exists()
        with open(log_dir / 'training_metrics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert len(data['epochs']) == 1
            assert data['mAP50'][0] == 0.72
            assert data['precision'][0] == 0.85


def test_calibrate_yolo_execution():
    """Verify YOLO temperature calibration script execution and parameter persistence."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cal_out = Path(tmp_dir) / "yolo_temp.json"

        # Test with synthetic fallback / uninitialized model
        T = calibrate_yolo(
            model_path="yolov8n.pt",
            val_data="data/external/rail_defects/data.yaml",
            output_path=str(cal_out),
            device="cpu"
        )

        assert 0.5 <= T <= 5.0
        assert cal_out.exists()
        with open(cal_out, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert "temperature" in data
            assert data["model"] == "yolo_visual_detector"
            assert data["status"] == "calibrated"
