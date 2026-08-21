"""
Enhanced PatchCore training pipeline with multi-scale feature extraction,
FAISS memory bank indexing, statistical calibration, and TPR/FPR benchmark validation.
"""
import os
import sys
import shutil
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml
import json
import numpy as np
from PIL import Image
from tqdm import tqdm

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    plt = None
    sns = None

from ml.models.vision.patchcore_enhanced import EnhancedPatchCore


def train_patchcore(
    data_config: str = "data/external/rail_normal_expanded/dataset_config.yaml",
    model_config: str = "ml/configs/patchcore_enhanced.yaml",
    output_dir: str = "artifacts/checkpoints/vision/patchcore_enhanced",
    device: str = "auto",
) -> EnhancedPatchCore:
    """Train Enhanced PatchCore model with multi-scale memory banks and calibration."""
    
    print("=" * 70)
    print("TrackChain Enhanced PatchCore Training Pipeline")
    print("=" * 70)
    
    # Resolve paths
    abs_data_cfg_path = Path(data_config) if Path(data_config).is_absolute() else repo_root / data_config
    abs_model_cfg_path = Path(model_config) if Path(model_config).is_absolute() else repo_root / model_config
    abs_out_dir = Path(output_dir) if Path(output_dir).is_absolute() else repo_root / output_dir
    abs_out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load model config
    if abs_model_cfg_path.exists():
        with open(abs_model_cfg_path, "r", encoding="utf-8") as f:
            model_cfg = yaml.safe_load(f) or {}
    else:
        model_cfg = {}
    
    # Load dataset config
    data_path_root = None
    train_rel = "train/good"
    valid_rel = "valid/good"
    defect_rel = "valid/defect"
    
    if abs_data_cfg_path.exists() and abs_data_cfg_path.is_file() and abs_data_cfg_path.suffix in [".yaml", ".yml"]:
        with open(abs_data_cfg_path, "r", encoding="utf-8") as f:
            data_cfg = yaml.safe_load(f) or {}
        raw_p = data_cfg.get("path", "")
        data_path_root = Path(raw_p) if Path(raw_p).is_absolute() else repo_root / raw_p
        train_rel = data_cfg.get("train", "train/good")
        valid_rel = data_cfg.get("valid", "valid/good")
        defect_rel = data_cfg.get("defect_valid", "valid/defect")
    elif abs_data_cfg_path.is_dir():
        data_path_root = abs_data_cfg_path
    else:
        # Fallback search
        for candidate in ["data/external/rail_normal_expanded", "data/external/rail_normal_only"]:
            cand_p = repo_root / candidate
            if (cand_p / "train" / "good").exists():
                data_path_root = cand_p
                break
    
    if data_path_root is None or not (data_path_root / train_rel).exists():
        raise FileNotFoundError(f"Normal training dataset not found at {data_path_root}")
    
    m_info = model_cfg.get("model", {})
    t_info = model_cfg.get("training", {})
    c_info = model_cfg.get("calibration", {})
    i_info = model_cfg.get("inference", {})
    
    # 1. Initialize Model
    print("\n[1/6] Initializing Enhanced PatchCore...")
    model = EnhancedPatchCore(
        backbone=m_info.get("backbone", "wide_resnet50_2"),
        layers=m_info.get("layers", ["layer2", "layer3"]),
        patch_sizes=m_info.get("patch_sizes", [3, 5, 7]),
        coreset_ratio=m_info.get("coreset_ratio", 0.08),
        dimension_reduction=m_info.get("dimension_reduction", True),
        target_dim=m_info.get("target_dim", 128),
        device=device,
        patch_weights=i_info.get("patch_weights", None),
        threshold=i_info.get("threshold", 0.50),
    )
    print(f"  Backbone:       {model.backbone_name}")
    print(f"  Layers:         {model.layers}")
    print(f"  Patch Sizes:    {model.patch_sizes}")
    print(f"  Coreset Ratio:  {model.coreset_ratio:.1%}")
    print(f"  Dim Reduction:  {model.dimension_reduction} (target={model.target_dim})")
    print(f"  Device:         {model.device}")
    
    # 2. Collect normal training images
    print("\n[2/6] Loading normal training images...")
    train_dir = data_path_root / train_rel
    train_images = sorted(list(train_dir.glob("*.jpg")) + list(train_dir.glob("*.png")))
    print(f"  Found {len(train_images)} normal training images in {train_dir}")
    
    if not train_images:
        raise ValueError(f"No training images found in {train_dir}")
    
    # 3. Build memory banks
    print("\n[3/6] Building multi-scale memory banks...")
    batch_size = t_info.get("batch_size", 32)
    num_workers = t_info.get("num_workers", 0)
    model.build_memory_bank(train_images, batch_size=batch_size, num_workers=num_workers)
    
    # 4. Calibrate thresholds on normal validation set
    print("\n[4/6] Calibrating thresholds on normal validation track...")
    valid_dir = data_path_root / valid_rel
    valid_images = sorted(list(valid_dir.glob("*.jpg")) + list(valid_dir.glob("*.png")))
    
    max_calib = c_info.get("validation_samples", 100)
    if len(valid_images) > max_calib:
        random.seed(42)
        calib_images = random.sample(valid_images, max_calib)
    elif valid_images:
        calib_images = valid_images
    else:
        calib_images = train_images[:min(50, len(train_images))]
    
    target_fpr = c_info.get("target_fpr", 0.01)
    model.calibrate(calib_images, target_fpr=target_fpr)
    
    # 5. Benchmark on defect validation set
    print("\n[5/6] Validating anomaly separation on defect benchmark...")
    defect_dir = data_path_root / defect_rel
    defect_images = sorted(list(defect_dir.glob("*.jpg")) + list(defect_dir.glob("*.png"))) if defect_dir.exists() else []
    
    validation_metrics: Dict[str, Any] = {}
    
    if defect_images:
        print(f"  Found {len(defect_images)} defect validation samples in {defect_dir}")
        defect_scores = []
        normal_scores = []
        
        for d_path in tqdm(defect_images, desc="Evaluating defect samples"):
            try:
                pil_d = Image.open(d_path).convert("RGB")
                sc = model.predict(pil_d)
                defect_scores.append(sc["ensemble"])
            except Exception:
                continue
        
        eval_normals = valid_images if valid_images else train_images[:min(60, len(train_images))]
        for n_path in tqdm(eval_normals, desc="Evaluating normal samples"):
            try:
                pil_n = Image.open(n_path).convert("RGB")
                sc = model.predict(pil_n)
                normal_scores.append(sc["ensemble"])
            except Exception:
                continue
        
        defect_scores = np.array(defect_scores)
        normal_scores = np.array(normal_scores)
        
        calib_ensemble = model.calibration_params.get("ensemble", {})
        threshold = calib_ensemble.get("threshold", float(np.percentile(normal_scores, 99.0)))
        
        tpr = float(np.mean(defect_scores >= threshold)) if len(defect_scores) > 0 else 0.0
        fpr = float(np.mean(normal_scores >= threshold)) if len(normal_scores) > 0 else 0.0
        
        print(f"\n  Validation Results:")
        print(f"    True Positive Rate (TPR):  {tpr:.1%} ({len(defect_scores)} defect samples)")
        print(f"    False Positive Rate (FPR): {fpr:.1%} ({len(normal_scores)} normal samples)")
        print(f"    P99 Threshold:             {threshold:.2f}")
        print(f"    Defect Mean Score:         {defect_scores.mean():.2f} (std={defect_scores.std():.2f})")
        print(f"    Normal Mean Score:         {normal_scores.mean():.2f} (std={normal_scores.std():.2f})")
        
        # Save validation metrics JSON
        validation_metrics = {
            "true_positive_rate": tpr,
            "false_positive_rate": fpr,
            "threshold": threshold,
            "num_defect_samples": len(defect_scores),
            "num_normal_samples": len(normal_scores),
            "defect_score_mean": float(defect_scores.mean()),
            "defect_score_std": float(defect_scores.std()),
            "normal_score_mean": float(normal_scores.mean()),
            "normal_score_std": float(normal_scores.std()),
            "separation_margin": float(defect_scores.mean() - normal_scores.mean()),
        }
        
        # Plot score distribution
        if plt is not None and sns is not None:
            try:
                plt.figure(figsize=(10, 6))
                sns.kdeplot(normal_scores, label='Normal Track (Baseline)', color='green', fill=True, alpha=0.35)
                sns.kdeplot(defect_scores, label='Defect Track (Anomalies)', color='red', fill=True, alpha=0.35)
                plt.axvline(threshold, color='black', linestyle='--', label=f'Threshold ({threshold:.2f})')
                plt.xlabel('Multi-Scale Anomaly Distance (L2)')
                plt.ylabel('Density')
                plt.title('Enhanced PatchCore Multi-Scale Separation')
                plt.legend()
                
                plot_path = abs_out_dir / "score_distribution.png"
                plt.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"    Saved score distribution plot: {plot_path}")
            except Exception as e:
                print(f"    [WARNING] Plotting failed: {e}")
    else:
        print("  No defect validation samples found for TPR/FPR benchmark")
    
    with open(abs_out_dir / "validation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(validation_metrics, f, indent=2)
    
    # 6. Save model and copy calibration to canonical location
    print("\n[6/6] Saving Enhanced PatchCore artifacts...")
    model.save(abs_out_dir)
    
    # Standard calibration path
    std_calib = repo_root / "artifacts" / "calibration" / "patchcore_calibration.json"
    std_calib.parent.mkdir(parents=True, exist_ok=True)
    if (abs_out_dir / "calibration.json").exists():
        shutil.copy(abs_out_dir / "calibration.json", std_calib)
    
    # Also save unified validation metrics in artifacts/validation/patchcore
    val_canonical = repo_root / "artifacts" / "validation" / "patchcore"
    val_canonical.mkdir(parents=True, exist_ok=True)
    if (abs_out_dir / "validation_metrics.json").exists():
        shutil.copy(abs_out_dir / "validation_metrics.json", val_canonical / "validation_metrics.json")
    if (abs_out_dir / "score_distribution.png").exists():
        shutil.copy(abs_out_dir / "score_distribution.png", val_canonical / "score_distribution.png")
    
    print("\n" + "=" * 70)
    print("Enhanced PatchCore Training Complete!")
    print("=" * 70)
    print(f"Checkpoint Directory: {abs_out_dir}")
    print(f"Calibration JSON:     {std_calib}")
    print(f"Validation Metrics:   {val_canonical / 'validation_metrics.json'}")
    print("=" * 70)
    
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Enhanced PatchCore")
    parser.add_argument("--data", type=str, default="data/external/rail_normal_expanded/dataset_config.yaml", help="Path to dataset config or folder")
    parser.add_argument("--config", type=str, default="ml/configs/patchcore_enhanced.yaml", help="Path to model config")
    parser.add_argument("--output", type=str, default="artifacts/checkpoints/vision/patchcore_enhanced", help="Output directory")
    parser.add_argument("--device", type=str, default="auto", help="Compute device (auto, cpu, cuda)")
    
    args = parser.parse_args()
    
    train_patchcore(
        data_config=args.data,
        model_config=args.config,
        output_dir=args.output,
        device=args.device
    )
