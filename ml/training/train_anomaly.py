"""
TrackChain Master PatchCore Anomaly Detector Training Pipeline.
Implements:
- Multi-scale feature extraction across layer2 + layer3
- Greedy Minimax / K-Center Core-set subsampling
- Optional dimension reduction via SparseRandomProjection
- Statistical calibration (P99 + Sigmoid fitting)
- Defect benchmark validation (TPR, FPR, score statistics)
- Serialization to ModelRegistry checkpoints and calibration manifests
"""

import argparse
import os
import json
import random
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import torch
from PIL import Image
import yaml
from sklearn.random_projection import SparseRandomProjection

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    plt = None
    sns = None

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
    Reduces feature memory size while maximizing spatial manifold coverage.
    """
    n_samples = len(features)
    target_count = max(10, int(n_samples * sampling_ratio))

    if target_count >= n_samples:
        return features

    np.random.seed(random_seed)
    selected_indices = [int(np.random.choice(n_samples))]
    
    first_center = features[selected_indices[0]:selected_indices[0] + 1]
    min_distances = np.linalg.norm(features - first_center, axis=1)

    print(f"[INFO] Running Greedy Core-set subsampling ({n_samples} -> {target_count} patches)...")
    for step in range(1, target_count):
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
    sampling_ratio: Optional[float] = None,
    device: Optional[str] = "auto",
    output_checkpoint: Optional[str] = None,
    output_calibration: Optional[str] = None,
    output_validation: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Full training pipeline for Enhanced PatchCore:
    1. Extract patch features from normal training images.
    2. Subsample features using core-set selection.
    3. Build FAISS nearest-neighbor search index.
    4. Compute P99 threshold on normal validation images and fit Sigmoid calibrator.
    5. Benchmark on defect validation set (TPR / FPR).
    6. Save memory bank (.npz) and calibration (.json).
    """
    repo_root = ModelRegistry.ROOT
    abs_data_dir = Path(data_dir) if Path(data_dir).is_absolute() else repo_root / data_dir
    abs_config_path = Path(config_path) if Path(config_path).is_absolute() else repo_root / config_path

    # Fallback to expanded dataset if original missing
    if not (abs_data_dir / "train" / "good").exists():
        expanded = repo_root / "data" / "external" / "rail_normal_expanded"
        if (expanded / "train" / "good").exists():
            abs_data_dir = expanded

    if device in ["auto", None, ""]:
        actual_device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        actual_device = "cuda" if device.startswith("cuda") or device == "0" else device

    # Load configuration
    cfg = {}
    if abs_config_path.exists():
        with open(abs_config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    model_cfg = cfg.get("model", {})
    calib_cfg = cfg.get("calibration", {})

    backbone_name = model_cfg.get("backbone", "wide_resnet50_2")
    coreset_ratio = sampling_ratio or model_cfg.get("coreset_sampling_ratio", 0.08)
    percentile = calib_cfg.get("threshold_percentile", 99.0)
    sigmoid_k = calib_cfg.get("sigmoid_k", 0.5)
    dim_reduction = model_cfg.get("dimension_reduction", False)
    target_dim = model_cfg.get("target_dim", 128)
    patch_size = model_cfg.get("patch_size", 3)

    print("=" * 70)
    print("TrackChain — Enhanced PatchCore Visual Anomaly Detector Training")
    print("=" * 70)
    print(f"Backbone:        {backbone_name}")
    print(f"Normal Dataset:  {abs_data_dir}")
    print(f"Patch Size:      {patch_size}x{patch_size}")
    print(f"Coreset Ratio:   {coreset_ratio:.1%}")
    print(f"Calib P99 Target:{percentile}%")
    print(f"Compute Device:  {actual_device}")

    train_good_dir = abs_data_dir / "train" / "good"
    valid_good_dir = abs_data_dir / "valid" / "good"
    defect_dir = abs_data_dir / "valid" / "defect"

    if not train_good_dir.exists():
        raise FileNotFoundError(f"Training normal images directory not found: {train_good_dir}")

    train_images = sorted(list(train_good_dir.glob("*.jpg")) + list(train_good_dir.glob("*.png")))
    valid_images = sorted(list(valid_good_dir.glob("*.jpg")) + list(valid_good_dir.glob("*.png")))

    if not train_images:
        raise ValueError(f"No normal training images found in {train_good_dir}")

    print(f"\n[1/5] Loaded {len(train_images)} normal training images, {len(valid_images)} validation images.")

    # Initialize detector backbone
    detector = PatchCoreAnomalyDetector(
        backbone_name=backbone_name,
        device=actual_device,
        patch_size=patch_size,
    )
    transform = get_default_transform(224)

    # 1. Extract patch features
    print("\n[2/5] Extracting multi-scale patch embeddings from normal track...")
    all_patch_features: List[np.ndarray] = []

    with torch.no_grad():
        for i, img_path in enumerate(train_images):
            try:
                img = Image.open(img_path).convert("RGB")
                tensor = transform(img).unsqueeze(0).to(detector.device)
                feats, _ = detector.extract_features(tensor)
                all_patch_features.append(feats.cpu().numpy().astype(np.float32))
            except Exception:
                continue

    raw_memory_bank = np.concatenate(all_patch_features, axis=0)
    print(f"      Extracted {raw_memory_bank.shape[0]} raw normal patch embeddings (Dim={raw_memory_bank.shape[1]}).")

    # Optional dimension reduction
    projector = None
    if dim_reduction and raw_memory_bank.shape[1] > target_dim:
        print(f"      Applying SparseRandomProjection ({raw_memory_bank.shape[1]} -> {target_dim})...")
        projector = SparseRandomProjection(n_components=target_dim, random_state=42)
        raw_memory_bank = projector.fit_transform(raw_memory_bank).astype(np.float32)

    # 2. Core-set subsampling
    print("\n[3/5] Performing Minimax Core-set selection...")
    coreset_memory_bank = greedy_coreset_subsampling(
        raw_memory_bank,
        sampling_ratio=coreset_ratio,
    )
    print(f"      Retained {coreset_memory_bank.shape[0]} diverse representative patches.")

    # Build FAISS nearest neighbor search index
    detector.set_memory_bank(coreset_memory_bank, projector=projector)

    # 3. Calibration on normal validation set
    print("\n[4/5] Establishing statistical P99 calibration threshold on normal validation track...")
    valid_distances: List[float] = []
    val_pool = valid_images if valid_images else train_images[:min(50, len(train_images))]

    for v_path in val_pool:
        try:
            v_img = Image.open(v_path).convert("RGB")
            dist, _ = detector.predict_raw(v_img)
            valid_distances.append(dist)
        except Exception:
            continue

    calibrator = SigmoidDistanceCalibrator(steepness_k=sigmoid_k, percentile=percentile)
    p99_thresh = calibrator.fit(valid_distances, percentile=percentile)
    print(f"      Normal Baseline: Mean={np.mean(valid_distances):.2f}, Max={np.max(valid_distances):.2f}, P99 Threshold={p99_thresh:.2f}")

    # 4. Defect validation benchmark
    print("\n[5/5] Benchmarking on defect validation set (TPR / FPR analysis)...")
    val_out_dir = Path(output_validation or "artifacts/validation/patchcore")
    val_out_dir.mkdir(parents=True, exist_ok=True)
    
    validation_metrics: Dict[str, Any] = {
        "p99_threshold": float(p99_thresh),
        "normal_mean_dist": float(np.mean(valid_distances)),
        "normal_max_dist": float(np.max(valid_distances)),
        "num_normal_samples": len(valid_distances),
        "memory_bank_patches": int(coreset_memory_bank.shape[0]),
        "feature_dim": int(coreset_memory_bank.shape[1]),
    }

    if defect_dir.exists():
        defect_images = sorted(list(defect_dir.glob("*.jpg")) + list(defect_dir.glob("*.png")))
        if defect_images:
            defect_distances: List[float] = []
            for d_path in defect_images:
                try:
                    d_img = Image.open(d_path).convert("RGB")
                    dist, _ = detector.predict_raw(d_img)
                    defect_distances.append(dist)
                except Exception:
                    continue

            if defect_distances:
                tpr = float(np.mean([d >= p99_thresh for d in defect_distances]))
                fpr = float(np.mean([n >= p99_thresh for n in valid_distances]))
                validation_metrics["true_positive_rate"] = tpr
                validation_metrics["false_positive_rate"] = fpr
                validation_metrics["defect_mean_dist"] = float(np.mean(defect_distances))
                validation_metrics["num_defect_samples"] = len(defect_distances)

                print(f"      True Positive Rate (TPR):  {tpr:.1%} ({len(defect_distances)} defect samples)")
                print(f"      False Positive Rate (FPR): {fpr:.1%} ({len(valid_distances)} normal samples)")

                # Plot distribution if matplotlib available
                if plt is not None and sns is not None:
                    try:
                        plt.figure(figsize=(9, 5))
                        sns.kdeplot(valid_distances, label='Normal Track (Baseline)', color='green', fill=True, alpha=0.4)
                        sns.kdeplot(defect_distances, label='Defect Track (Anomalies)', color='red', fill=True, alpha=0.4)
                        plt.axvline(p99_thresh, color='black', linestyle='--', label=f'P99 Threshold ({p99_thresh:.2f})')
                        plt.xlabel('PatchCore Nearest-Neighbor L2 Distance')
                        plt.ylabel('Density')
                        plt.title('PatchCore Visual Anomaly Separation')
                        plt.legend()
                        plot_path = val_out_dir / "patchcore_score_distribution.png"
                        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
                        plt.close()
                        print(f"      Saved score distribution plot: {plot_path}")
                    except Exception:
                        pass

    with open(val_out_dir / "validation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(validation_metrics, f, indent=2)

    # 5. Save artifacts to canonical destinations
    ckpt_path = Path(output_checkpoint) if output_checkpoint else ModelRegistry.get_trained_weights("vision", "patchcore_memory_bank.npz")
    calib_path = Path(output_calibration) if output_calibration else ModelRegistry.get_calibration_path("patchcore")

    detector.save_memory_bank(ckpt_path)
    calibrator.save(calib_path)

    # Copy calibration to standard location
    std_calib = repo_root / "artifacts" / "calibration" / "patchcore_calibration.json"
    std_calib.parent.mkdir(parents=True, exist_ok=True)
    calibrator.save(std_calib)

    print("\n" + "=" * 70)
    print("Enhanced PatchCore Training Complete!")
    print("=" * 70)
    print(f"Memory Bank Checkpoint: {ckpt_path}")
    print(f"Calibration JSON:       {calib_path}")
    print(f"Validation Metrics:     {val_out_dir / 'validation_metrics.json'}")

    return str(ckpt_path), str(calib_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Enhanced PatchCore Visual Anomaly Detector.")
    parser.add_argument("--data", default="data/external/rail_normal_only", help="Path to normal dataset directory")
    parser.add_argument("--config", default="ml/configs/anomaly.yaml", help="Path to anomaly.yaml")
    parser.add_argument("--coreset_ratio", "--ratio", dest="coreset_ratio", type=float, default=None, help="Coreset subsampling ratio")
    parser.add_argument("--device", default="auto", help="Device ('auto', 'cuda', or 'cpu')")
    parser.add_argument("--out-ckpt", default=None, help="Output memory bank path")
    parser.add_argument("--out-calib", default=None, help="Output calibration JSON path")
    args = parser.parse_args()

    train_patchcore(
        data_dir=args.data,
        config_path=args.config,
        sampling_ratio=args.coreset_ratio,
        device=args.device,
        output_checkpoint=args.out_ckpt,
        output_calibration=args.out_calib,
    )
