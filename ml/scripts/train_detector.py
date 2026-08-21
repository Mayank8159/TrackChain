# Train YOLOv8n detector on railway track defect dataset with Ultralytics (tc.v1).

import argparse
import os
import sys
import shutil
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    import torch
except ImportError:
    torch = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from ml.core.registry import ModelRegistry


def resolve_device(requested_device: Optional[str] = None) -> str:
    """Resolve compute device: auto-detects CUDA GPU if available."""
    if requested_device and requested_device not in ["auto", ""]:
        return str(requested_device)
    if torch is not None and torch.cuda.is_available():
        return "0"
    return "cpu"


def train_yolo_detector(
    data_yaml: str = "data/external/rail_defects/data.yaml",
    config_path: str = "ml/configs/detector.yaml",
    epochs: int = 100,
    batch_size: int = 16,
    img_size: int = 640,
    device: Optional[str] = "auto",
    output_dir: Optional[str] = None,
):
    if YOLO is None:
        raise RuntimeError("Ultralytics is required for training. Install with: pip install ultralytics")

    abs_repo = ModelRegistry.ROOT
    abs_data_yaml = Path(data_yaml) if Path(data_yaml).is_absolute() else abs_repo / data_yaml
    abs_config_path = Path(config_path) if Path(config_path).is_absolute() else abs_repo / config_path
    
    if output_dir:
        abs_output_dir = Path(output_dir) if Path(output_dir).is_absolute() else abs_repo / output_dir
    else:
        abs_output_dir = ModelRegistry.CHECKPOINTS_DIR / "vision"

    target_device = resolve_device(device)

    # Sanitize and dynamically set path in data.yaml for current OS/environment
    if abs_data_yaml.exists():
        with open(abs_data_yaml, "r") as f:
            dy = yaml.safe_load(f) or {}
        dataset_dir = abs_data_yaml.parent.resolve().as_posix()
        if dy.get("path") != dataset_dir:
            dy["path"] = dataset_dir
            with open(abs_data_yaml, "w") as f:
                yaml.dump(dy, f, sort_keys=False)

    print(f"[INFO] Starting TrackChain YOLOv8n Training Pipeline")
    print(f"       Dataset YAML: {abs_data_yaml}")
    print(f"       Config:       {abs_config_path}")
    print(f"       Output Dir:   {abs_output_dir}")
    print(f"       Device:       {target_device}")
    print(f"       Epochs:       {epochs}")
    print(f"       Batch Size:   {batch_size}")

    # Load custom hyperparameters if config exists
    cfg = {}
    if abs_config_path.exists():
        with open(abs_config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}

    train_cfg = cfg.get("training", {})
    aug_cfg = cfg.get("augmentations", {})

    optimizer = train_cfg.get("optimizer", "AdamW")
    lr0 = train_cfg.get("lr0", 0.001)
    cos_lr = train_cfg.get("cos_lr", True)
    close_mosaic = train_cfg.get("close_mosaic", 10)

    # Initialize from base weights if available
    base_weights = ModelRegistry.get_base_weights("vision", "yolov8n.pt")
    model_init = str(base_weights) if base_weights.exists() else "yolov8n.pt"
    model = YOLO(model_init)

    # Train model with SOTA domain augmentations
    results = model.train(
        data=str(abs_data_yaml),
        epochs=epochs,
        batch=batch_size,
        imgsz=img_size,
        device=target_device,
        optimizer=optimizer,
        lr0=lr0,
        cos_lr=cos_lr,
        close_mosaic=close_mosaic,
        # Augmentations for railway high-speed conditions
        hsv_h=aug_cfg.get("hsv_h", 0.015),
        hsv_s=aug_cfg.get("hsv_s", 0.7),
        hsv_v=aug_cfg.get("hsv_v", 0.4),
        degrees=aug_cfg.get("degrees", 5.0),
        translate=aug_cfg.get("translate", 0.1),
        scale=aug_cfg.get("scale", 0.5),
        shear=aug_cfg.get("shear", 2.0),
        perspective=aug_cfg.get("perspective", 0.0001),
        fliplr=aug_cfg.get("fliplr", 0.5),
        mosaic=aug_cfg.get("mosaic", 1.0),
        mixup=aug_cfg.get("mixup", 0.1),
        erasing=aug_cfg.get("cutout", 0.1),
        # Output paths
        project=str(abs_output_dir),
        name="yolov8n_rail_run",
        exist_ok=True,
        verbose=True,
    )

    # Copy best weights to canonical checkpoint locations
    best_pt = abs_output_dir / "yolov8n_rail_run" / "weights" / "best.pt"
    canonical_best = abs_output_dir / "yolov8n_rail_best.pt"
    alias_best = abs_output_dir / "yolo_rail_v0.1.pt"

    if best_pt.exists():
        shutil.copy(best_pt, canonical_best)
        shutil.copy(best_pt, alias_best)
        print(f"[OK] Checkpoint saved: {canonical_best} and {alias_best}")

    print(f"\n[SUCCESS] Training completed. Best model saved in {canonical_best}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train TrackChain YOLOv8n defect detector.")
    parser.add_argument("--data", default="data/external/rail_defects/data.yaml", help="Path to data.yaml")
    parser.add_argument("--config", default="ml/configs/detector.yaml", help="Path to detector.yaml")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--device", default="auto", help="Device to train on ('auto', '0' for CUDA GPU, or 'cpu')")
    parser.add_argument("--output-dir", default=None, help="Output directory for checkpoints")
    args = parser.parse_args()

    train_yolo_detector(
        data_yaml=args.data,
        config_path=args.config,
        epochs=args.epochs,
        batch_size=args.batch,
        device=args.device,
        output_dir=args.output_dir,
    )
