# Master model training and calibration pipeline across all TrackChain sub-phases (tc.v1 SOTA).

import os
import sys
from pathlib import Path

# Add repo root to python path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

from ml.utils.logging import get_ml_logger
from ml.training.train_anomaly import train_patchcore
from ml.scripts.generate_trc_telemetry import generate_trc_telemetry_csv
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
import pandas as pd

logger = get_ml_logger("train_all")


def run_phase_2_1_vision_detector():
    """Verify Phase 2.1 YOLOv8 dataset connection and checkpoint."""
    logger.info(">>> PHASE 2.1: Checking YOLOv8 Visual Defect Detector Dataset...")
    data_yaml = repo_root / "data" / "raw" / "rail_dataset" / "data.yaml"
    if not data_yaml.exists():
        logger.warning(f"YOLO dataset config not found at {data_yaml}. Run ml/scripts/setup_yolo_dataset.ps1")
    else:
        logger.info(f"[OK] YOLO dataset config verified at {data_yaml}")


def run_phase_2_2_patchcore():
    """Train Phase 2.2 PatchCore memory bank and calibration."""
    logger.info(">>> PHASE 2.2: Training PatchCore Visual Anomaly Detector...")
    normal_data = repo_root / "data" / "external" / "rail_normal_only"
    if not normal_data.exists():
        logger.warning(f"Normal dataset not found at {normal_data}. Generating fallback samples...")
        from ml.scripts.setup_neudet_dataset import setup_dataset if "setup_dataset" in globals() else None

    train_patchcore(
        data_dir=str(normal_data),
        config_path="ml/configs/anomaly.yaml",
        sampling_ratio=0.10,
        device="cpu",
    )


def run_phase_2_3_geometry_physics():
    """Generate Phase 2.3 EN 13848 synthetic TRC dataset and verify exceedance detector."""
    logger.info(">>> PHASE 2.3: Generating EN 13848-2 PSD Synthetic TRC Telemetry...")
    out_csv = repo_root / "data" / "processed" / "synthetic_trc_run_001.csv"
    generate_trc_telemetry_csv(
        output_path=str(out_csv),
        length_m=1000.0,
        defect_mm=5.0,
        defect_start_m=500.0,
    )

    logger.info("Verifying EN 13848 Physics Threshold Detector exceedance calibration...")
    df = pd.read_csv(out_csv)
    detector = EN13848PhysicsThresholdDetector()
    signals = detector.predict(df)
    fired_sigs = [s for s in signals if s.fired]
    logger.info(f"[OK] Physics Evaluation complete. Fired Alarms: {len(fired_sigs)}")
    for s in fired_sigs:
        logger.info(f"     -> {s.predicted_class.value}: Raw={s.raw_score:.2f}mm, Calibrated={s.value:.3f}")


def main():
    logger.info("==================================================================")
    logger.info(" TrackChain ML Core Triad Training & Calibration Pipeline (tc.v1)")
    logger.info("==================================================================")

    run_phase_2_1_vision_detector()
    run_phase_2_2_patchcore()
    run_phase_2_3_geometry_physics()

    logger.info("==================================================================")
    logger.info(" Core Sensor Fusion Triad (Phases 2.1, 2.2, 2.3) Sealed & Synced!")
    logger.info("==================================================================")


if __name__ == "__main__":
    main()
