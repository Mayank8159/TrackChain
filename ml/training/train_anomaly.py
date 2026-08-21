"""
TrackChain Master PatchCore Anomaly Detector Training Pipeline (tc.v1 SOTA).
Implements:
- Batched multi-scale feature extraction across layer2 + layer3
- Fast Vectorized Greedy Minimax / K-Center Core-set subsampling (O(N) memory, fast PyTorch/NumPy matrix acceleration)
- Dimension reduction via SparseRandomProjection
- Statistical calibration (P99 + Sigmoid fitting)
- Defect benchmark validation (TPR, FPR, score separation)
- Serialization to ModelRegistry checkpoints and calibration manifests
"""

import argparse
import os
import json
import random
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
import yaml
from sklearn.random_projection import SparseRandomProjection
from tqdm import tqdm

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


class ImageDataset(torch.utils.data.Dataset):
    """Batched image dataset loader for fast PatchCore feature extraction."""

    def __init__(self, image_paths: List[Path], transform=None):
        self.image_paths = [Path(p) for p in image_paths]
        self.transform = transform or get_default_transform(224)

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        try:
            pil_img = Image.open(img_path).convert("RGB")
            return self.transform(pil_img)
        except Exception:
            return torch.zeros((3, 224, 224), dtype=torch.float32)


def fast_greedy_coreset_subsampling(
    features: np.ndarray,
    sampling_ratio: float = 0.08,
    max_coreset_size: int = 3000,
    max_candidate_pool: int = 40000,
    random_seed: int = 42,
) -> np.ndarray:
    """
    High-performance Vectorized Greedy Minimax / K-Center Core-set subsampling.
    Accelerated with candidate pool filtering and vectorized squared distance updates.
    """
    n_samples = len(features)
    if n_samples == 0:
        return features

    # 1. Pre-filter candidate pool if excessively large (preserves manifold coverage without quadratic explosion)
    np.random.seed(random_seed)
    if n_samples > max_candidate_pool:
        candidate_indices = np.random.choice(n_samples, max_candidate_pool, replace=False)
        candidate_features = features[candidate_indices]
    else:
        candidate_features = features

    n_candidates = len(candidate_features)
    target_count = max(10, min(max_coreset_size, int(n_candidates * sampling_ratio)))

    if target_count >= n_candidates:
        return candidate_features

    print(f"[INFO] Running Accelerated Core-set selection ({n_candidates} candidates -> {target_count} representative patches)...")

    # Use PyTorch tensor on CPU/GPU for fast BLAS/LAPACK matrix operations
    feat_tensor = torch.from_numpy(candidate_features).float()
    selected_indices = [int(np.random.choice(n_candidates))]

    # Initial distances to first chosen center
    first_center = feat_tensor[selected_indices[0]:selected_indices[0] + 1]
    # Squared Euclidean distance: ||x - c||^2
    min_sq_dists = torch.sum((feat_tensor - first_center) ** 2, dim=1)

    pbar = tqdm(total=target_count, desc="Minimax Coreset Selection", unit="patch")
    pbar.update(1)

    step = 1
    while step < target_count:
        new_idx = int(torch.argmax(min_sq_dists).item())
        selected_indices.append(new_idx)

        new_center = feat_tensor[new_idx:new_idx + 1]
        new_sq_dists = torch.sum((feat_tensor - new_center) ** 2, dim=1)
        min_sq_dists = torch.minimum(min_sq_dists, new_sq_dists)

        step += 1
        pbar.update(1)

    pbar.close()
    return candidate_features[selected_indices]


# Backwards compatibility alias
greedy_coreset_subsampling = fast_greedy_coreset_subsampling


def train_patchcore(
    data_dir: str = "data/external/rail_normal_only",
    config_path: str = "ml/configs/anomaly.yaml",
    sampling_ratio: Optional[float] = None,
    max_coreset_size: int = 3000,
    batch_size: int = 32,
    device: Optional[str] = "auto",
    output_checkpoint: Optional[str] = None,
    output_calibration: Optional[str] = None,
    output_validation: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Full training pipeline for Enhanced PatchCore:
    1. Extract patch features from normal training images with batching.
    2. Subsample features using fast core-set selection.
    3. Build FAISS nearest-neighbor search index.
    4. Compute P99 threshold on normal validation images and fit Sigmoid calibrator.
    5. Benchmark on defect validation set (TPR / FPR).
    6. Save memory bank (.npz) and calibration (.json).
    """
    repo_root = ModelRegistry.ROOT
    abs_data_dir = Path(data_dir) if Path(data_dir).is_absolute() else repo_root / data_dir
    abs_config_path = Path(config_path) if Path(config_path).is_absolute() else repo_root / config_path

    # Fallback search for normal dataset
    if not (abs_data_dir / "train" / "good").exists():
        for candidate in ["data/external/rail_normal_expanded", "data/external/rail_normal_only"]:
            cand_p = repo_root / candidate
            if (cand_p / "train" / "good").exists():
                abs_data_dir = cand_p
                break

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

    print("=" * 75)
    print("TrackChain — Enhanced PatchCore Visual Anomaly Detector Training (tc.v1 SOTA)")
    print("=" * 75)
    print(f"Backbone:        {backbone_name}")
    print(f"Normal Dataset:  {abs_data_dir}")
    print(f"Patch Size:      {patch_size}x{patch_size}")
    print(f"Coreset Ratio:   {coreset_ratio:.1%} (Max Coreset: {max_coreset_size})")
    print(f"Batch Size:      {batch_size}")
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

    # 1. Extract patch features using batched DataLoader for maximum throughput
    print("\n[2/5] Extracting multi-scale patch embeddings from normal track...")
    all_patch_features: List[np.ndarray] = []

    dataset = ImageDataset(train_images, transform=transform)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    start_extract = time.time()
    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Extracting normal patch embeddings"):
            tensor = batch.to(detector.device)
            feats, _ = detector.extract_features(tensor)
            all_patch_features.append(feats.cpu().numpy().astype(np.float32))

    raw_memory_bank = np.concatenate(all_patch_features, axis=0)
    extract_time = time.time() - start_extract
    print(f"      Extracted {raw_memory_bank.shape[0]} raw normal patch embeddings in {extract_time:.1f}s (Dim={raw_memory_bank.shape[1]}).")

    # Optional dimension reduction
    projector = None
    if dim_reduction and raw_memory_bank.shape[1] > target_dim:
        print(f"      Applying SparseRandomProjection ({raw_memory_bank.shape[1]} -> {target_dim})...")
        projector = SparseRandomProjection(n_components=target_dim, random_state=42)
        raw_memory_bank = projector.fit_transform(raw_memory_bank).astype(np.float32)

    # 2. Core-set subsampling
    print("\n[3/5] Performing Accelerated Minimax Core-set selection...")
    start_coreset = time.time()
    coreset_memory_bank = fast_greedy_coreset_subsampling(
        raw_memory_bank,
        sampling_ratio=coreset_ratio,
        max_coreset_size=max_coreset_size,
    )
    coreset_time = time.time() - start_coreset
    print(f"      Retained {coreset_memory_bank.shape[0]} representative patches in {coreset_time:.1f}s.")

    # Build FAISS nearest neighbor search index
    detector.set_memory_bank(coreset_memory_bank, projector=projector)

    # 3. Calibration on normal validation set
    print("\n[4/5] Establishing statistical P99 calibration threshold on normal validation track...")
    valid_distances: List[float] = []
    val_pool = valid_images if valid_images else train_images[:min(60, len(train_images))]

    for v_path in tqdm(val_pool, desc="Calibrating on normal validation track"):
        try:
            v_img = Image.open(v_path).convert("RGB")
            dist, _ = detector.predict_raw(v_img)
            valid_distances.append(float(dist))
        except Exception:
            continue

    if not valid_distances:
        valid_distances = [1.0]

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
        "backbone": backbone_name,
    }

    if defect_dir.exists():
        defect_images = sorted(list(defect_dir.glob("*.jpg")) + list(defect_dir.glob("*.png")))
        if defect_images:
            defect_distances: List[float] = []
            for d_path in tqdm(defect_images, desc="Evaluating defect validation samples"):
                try:
                    d_img = Image.open(d_path).convert("RGB")
                    dist, _ = detector.predict_raw(d_img)
                    defect_distances.append(float(dist))
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

    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    calib_path.parent.mkdir(parents=True, exist_ok=True)

    detector.save_memory_bank(ckpt_path)
    calibrator.save(calib_path)

    # Copy calibration to standard location
    std_calib = repo_root / "artifacts" / "calibration" / "patchcore_calibration.json"
    std_calib.parent.mkdir(parents=True, exist_ok=True)
    calibrator.save(std_calib)

    print("\n" + "=" * 75)
    print("Enhanced PatchCore Training Complete!")
    print("=" * 75)
    print(f"Memory Bank Checkpoint: {ckpt_path}")
    print(f"Calibration JSON:       {calib_path}")
    print(f"Standard Calibration:   {std_calib}")
    print(f"Validation Metrics:     {val_out_dir / 'validation_metrics.json'}")
    print("=" * 75)

    return str(ckpt_path), str(calib_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Enhanced PatchCore Visual Anomaly Detector (tc.v1 SOTA).")
    parser.add_argument("--data", default="data/external/rail_normal_only", help="Path to normal dataset directory")
    parser.add_argument("--config", default="ml/configs/anomaly.yaml", help="Path to anomaly.yaml")
    parser.add_argument("--coreset_ratio", "--ratio", dest="coreset_ratio", type=float, default=None, help="Coreset subsampling ratio")
    parser.add_argument("--max_coreset", type=int, default=3000, help="Maximum number of coreset representative patches")
    parser.add_argument("--batch_size", "--batch", type=int, default=32, help="Feature extraction batch size")
    parser.add_argument("--device", default="auto", help="Device ('auto', 'cuda', or 'cpu')")
    parser.add_argument("--out-ckpt", default=None, help="Output memory bank path")
    parser.add_argument("--out-calib", default=None, help="Output calibration JSON path")
    args = parser.parse_args()

    train_patchcore(
        data_dir=args.data,
        config_path=args.config,
        sampling_ratio=args.coreset_ratio,
        max_coreset_size=args.max_coreset,
        batch_size=args.batch_size,
        device=args.device,
        output_checkpoint=args.out_ckpt,
        output_calibration=args.out_calib,
    )
