# Training pipeline for PatchCore memory bank extraction, core-set subsampling, and calibration (tc.v1 SOTA).

import argparse
import os
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import torch
from PIL import Image
import yaml

from ml.core.registry import ModelRegistry
from ml.models.vision.anomaly import PatchCoreAnomalyDetector, get_default_transform
from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator


def greedy_coreset_subsampling(
    features: np.ndarray,
    sampling_ratio: float = 0.10,
    random_seed: int = 42,
) -> np.ndarray:
    """
    Greedy Minimax / K-Center Core-set subsampling for PatchCore memory bank.
    Reduces feature memory size by (1 - sampling_ratio) while maximizing spatial coverage.
    """
    n_samples = len(features)
    target_count = max(10, int(n_samples * sampling_ratio))

    if target_count >= n_samples:
        return features

    np.random.seed(random_seed)
    # Pick first center randomly
    selected_indices = [np.random.choice(n_samples)]
    
    # Track min distance of all points to current center set
    first_center = features[selected_indices[0]:selected_indices[0] + 1]
    min_distances = np.linalg.norm(features - first_center, axis=1)

    print(f"[INFO] Running Greedy Core-set subsampling ({n_samples} -> {target_count} patches)...")
    for step in range(1, target_count):
        # Pick point with maximum distance to existing centers
        new_idx = int(np.argmax(min_distances))
        selected_indices.append(new_idx)

        new_center = features[new_idx:new_idx + 1]
        new_dists = np.linalg.norm(features - new_center, axis=1)
        min_distances = np.minimum(min_distances, new_dists)

        if (step + 1) % 500 == 0 or (step + 1) == target_count:
            print(f"       Subsampled {step + 1}/{target_count} representative patches ({(step + 1)/target_count:.0%})")

    return features[selected_indices]


def train_patchcore(
    data_dir: str = "data/external/rail_normal_only",
    config_path: str = "ml/configs/anomaly.yaml",
    sampling_ratio: float = 0.10,
    device: Optional[str] = "auto",
    output_checkpoint: Optional[str] = None,
    output_calibration: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Full training pipeline for PatchCore:
    1. Extract patch features from normal training images.
    2. Subsample features using core-set selection.
    3. Build nearest-neighbor search index.
    4. Compute P99 threshold on normal validation images and fit Sigmoid calibrator.
    5. Save memory bank (.npz) and calibration (.json).
    """
    repo_root = ModelRegistry.ROOT
    abs_data_dir = Path(data_dir) if Path(data_dir).is_absolute() else repo_root / data_dir
    abs_config_path = Path(config_path) if Path(config_path).is_absolute() else repo_root / config_path

    if device in ["auto", None, ""]:
        actual_device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        actual_device = "cuda" if device.startswith("cuda") or device == "0" else device

    # Load configuration
    cfg = {}
    if abs_config_path.exists():
        with open(abs_config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}

    model_cfg = cfg.get("model", {})
    calib_cfg = cfg.get("calibration", {})

    backbone_name = model_cfg.get("backbone", "wide_resnet50_2")
    coreset_ratio = sampling_ratio or model_cfg.get("coreset_sampling_ratio", 0.10)
    percentile = calib_cfg.get("threshold_percentile", 99.0)
    sigmoid_k = calib_cfg.get("sigmoid_k", 0.5)

    print("==================================================================")
    print(" TrackChain — Training PatchCore Visual Anomaly Detector")
    print("==================================================================")
    print(f" Backbone:        {backbone_name}")
    print(f" Normal Dataset:  {abs_data_dir}")
    print(f" Coreset Ratio:   {coreset_ratio:.1%}")
    print(f" Calib P99 Target:{percentile}%")

    train_good_dir = abs_data_dir / "train" / "good"
    valid_good_dir = abs_data_dir / "valid" / "good"

    if not train_good_dir.exists():
        raise FileNotFoundError(f"Training normal images directory not found: {train_good_dir}")

    # Gather images
    train_images = list(train_good_dir.glob("*.jpg")) + list(train_good_dir.glob("*.png"))
    valid_images = list(valid_good_dir.glob("*.jpg")) + list(valid_good_dir.glob("*.png"))

    if not train_images:
        raise ValueError(f"No normal training images found in {train_good_dir}")

    print(f"[INFO] Found {len(train_images)} normal training images, {len(valid_images)} validation images.")

    # Initialize detector backbone
    detector = PatchCoreAnomalyDetector(
        backbone_name=backbone_name,
        device=actual_device,
    )
    transform = get_default_transform(224)

    # 1. Extract patch features from all normal training images
    print("[INFO] Extracting multi-scale patch features from normal training images...")
    all_patch_features: List[np.ndarray] = []

    with torch.no_grad():
        for i, img_path in enumerate(train_images):
            img = Image.open(img_path).convert("RGB")
            tensor = transform(img).unsqueeze(0).to(detector.device)
            feats, _ = detector.extract_features(tensor)
            all_patch_features.append(feats.cpu().numpy())

    raw_memory_bank = np.concatenate(all_patch_features, axis=0)
    print(f"[OK] Extracted {raw_memory_bank.shape[0]} raw normal patch embeddings (Dim={raw_memory_bank.shape[1]}).")

    # 2. Core-set subsampling
    coreset_memory_bank = greedy_coreset_subsampling(
        raw_memory_bank,
        sampling_ratio=coreset_ratio,
    )
    print(f"[OK] Core-set subsampling completed: {coreset_memory_bank.shape[0]} representative patches retained.")

    # 3. Build nearest neighbor search index
    detector.set_memory_bank(coreset_memory_bank)

    # 4. Calibration on normal validation set
    valid_distances: List[float] = []
    if valid_images:
        print("[INFO] Running inference on normal validation images to establish P99 baseline...")
        for v_path in valid_images:
            v_img = Image.open(v_path).convert("RGB")
            dist, _ = detector.predict_raw(v_img)
            valid_distances.append(dist)
    else:
        # Fallback: compute self-distances on train subset
        for t_path in train_images[:6]:
            t_img = Image.open(t_path).convert("RGB")
            dist, _ = detector.predict_raw(t_img)
            valid_distances.append(dist)

    calibrator = SigmoidDistanceCalibrator(steepness_k=sigmoid_k, percentile=percentile)
    p99_thresh = calibrator.fit(valid_distances, percentile=percentile)
    print(f"[OK] Normal baseline distance distribution: Mean={np.mean(valid_distances):.2f}, Max={np.max(valid_distances):.2f}, P99 Threshold={p99_thresh:.2f}")

    # 5. Save artifacts to ModelRegistry destinations
    if output_checkpoint:
        ckpt_path = Path(output_checkpoint)
    else:
        ckpt_path = ModelRegistry.get_trained_weights("vision", "patchcore_memory_bank.npz")

    if output_calibration:
        calib_path = Path(output_calibration)
    else:
        calib_path = ModelRegistry.get_calibration_path("patchcore")

    detector.save_memory_bank(ckpt_path)
    calibrator.save(calib_path)

    print(f"\n[SUCCESS] PatchCore Training Complete!")
    print(f"          Memory Bank Checkpoint: {ckpt_path}")
    print(f"          Calibration JSON:       {calib_path}")

    return str(ckpt_path), str(calib_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train PatchCore visual anomaly detector.")
    parser.add_argument("--data", default="data/external/rail_normal_only", help="Path to normal dataset directory")
    parser.add_argument("--config", default="ml/configs/anomaly.yaml", help="Path to anomaly.yaml")
    parser.add_argument("--ratio", type=float, default=0.10, help="Coreset subsampling ratio")
    parser.add_argument("--device", default="cpu", help="Device ('cpu' or 'cuda')")
    parser.add_argument("--out-ckpt", default=None, help="Output memory bank path")
    parser.add_argument("--out-calib", default=None, help="Output calibration JSON path")
    args = parser.parse_args()

    train_patchcore(
        data_dir=args.data,
        config_path=args.config,
        sampling_ratio=args.ratio,
        device=args.device,
        output_checkpoint=args.out_ckpt,
        output_calibration=args.out_calib,
    )
