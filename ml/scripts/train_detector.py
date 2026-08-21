"""
TrackChain Master YOLO Detector Training Module.
Comprehensive training pipeline with:
- MetricsLogger callback logging loss, mAP50, mAP50-95, precision, recall, and learning rate
- ProgressiveTrainer resolution scheduling
- Domain-specific railway augmentations (mosaic, mixup, copy-paste, HSV, perspective, flips)
- Automatic device resolution (CUDA GPU auto-detection with CPU fallback)
- Canonical checkpoint synchronization with ModelRegistry
- Automatic post-training test split validation and final metrics persistence
"""

import argparse
import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import yaml

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


# ============================================================================
# Device Resolution
# ============================================================================

def resolve_device(requested_device: Optional[str] = None) -> str:
    """Resolve compute device: auto-detects CUDA GPU if available."""
    if requested_device and requested_device not in ["auto", "", None]:
        return str(requested_device)
    if torch is not None and torch.cuda.is_available():
        return "0"
    return "cpu"


# ============================================================================
# Custom Metrics Logger Callback
# ============================================================================

class MetricsLogger:
    """Log detailed training and validation metrics to JSON across epochs."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.log_dir / "training_metrics.json"
        self.metrics = {
            "epochs": [],
            "train_loss": [],
            "val_loss": [],
            "mAP50": [],
            "mAP50_95": [],
            "precision": [],
            "recall": [],
            "lr": [],
            "epoch_time_s": [],
        }
        self.start_time = time.time()
        self.last_epoch_time = self.start_time

    def on_fit_epoch_end(self, trainer):
        """Called at the end of each fit epoch when both train and val metrics exist."""
        try:
            epoch = getattr(trainer, "epoch", 0) + 1
            metrics_dict = getattr(trainer, "metrics", {}) or {}

            # Loss items
            loss_val = 0.0
            if hasattr(trainer, "loss_items") and trainer.loss_items is not None:
                loss_val = float(trainer.loss_items.mean().item())
            elif hasattr(trainer, "loss") and trainer.loss is not None:
                loss_val = float(trainer.loss.item())

            # Learning rate
            lr = 0.0
            if hasattr(trainer, "optimizer") and trainer.optimizer and trainer.optimizer.param_groups:
                lr = float(trainer.optimizer.param_groups[0]["lr"])

            map50 = float(metrics_dict.get("metrics/mAP50(B)", 0.0))
            map50_95 = float(metrics_dict.get("metrics/mAP50-95(B)", 0.0))
            precision = float(metrics_dict.get("metrics/precision(B)", 0.0))
            recall = float(metrics_dict.get("metrics/recall(B)", 0.0))

            now = time.time()
            elapsed_epoch = now - self.last_epoch_time
            self.last_epoch_time = now

            self.metrics["epochs"].append(epoch)
            self.metrics["train_loss"].append(loss_val)
            self.metrics["val_loss"].append(float(metrics_dict.get("val/loss", 0.0)))
            self.metrics["mAP50"].append(map50)
            self.metrics["mAP50_95"].append(map50_95)
            self.metrics["precision"].append(precision)
            self.metrics["recall"].append(recall)
            self.metrics["lr"].append(lr)
            self.metrics["epoch_time_s"].append(round(elapsed_epoch, 2))

            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=2)

            print(
                f"[TrackChain YOLO] Epoch {epoch:3d} | "
                f"Loss: {loss_val:.4f} | "
                f"mAP50: {map50:.4f} | "
                f"mAP50-95: {map50_95:.4f} | "
                f"P: {precision:.4f} | "
                f"R: {recall:.4f} | "
                f"LR: {lr:.6f}"
            )
        except Exception:
            # Prevent logging callback errors from interrupting training loop
            pass


# ============================================================================
# Progressive Trainer
# ============================================================================

class ProgressiveTrainer:
    """Implement progressive training schedule: start lower resolution, scale to target."""

    def __init__(self, base_imgsz: int = 416, final_imgsz: int = 640):
        self.base_imgsz = base_imgsz
        self.final_imgsz = final_imgsz

    def get_imgsz_for_epoch(self, epoch: int, total_epochs: int) -> int:
        if total_epochs <= 1:
            return self.final_imgsz
        progress = epoch / float(total_epochs)
        if progress < 0.30:
            return self.base_imgsz
        elif progress < 0.70:
            scale = (progress - 0.30) / 0.40
            imgsz = int(self.base_imgsz + scale * (self.final_imgsz - self.base_imgsz))
            return max(self.base_imgsz, min(self.final_imgsz, (imgsz // 32) * 32))
        else:
            return self.final_imgsz


# ============================================================================
# Core Training Function
# ============================================================================

def train_yolo_detector(
    data_yaml: str = "data/external/rail_defects/data.yaml",
    config_path: str = "ml/configs/detector.yaml",
    epochs: Optional[int] = None,
    batch_size: Optional[int] = None,
    img_size: Optional[int] = None,
    device: Optional[str] = "auto",
    output_dir: Optional[str] = None,
    resume: bool = False,
    run_name: str = "yolov8n_rail_run",
):
    """
    Unified training interface for TrackChain YOLO railway defect detector.
    """
    if YOLO is None:
        raise RuntimeError("Ultralytics is required for training. Install with: pip install ultralytics")

    abs_repo = ModelRegistry.ROOT
    abs_data_yaml = Path(data_yaml) if Path(data_yaml).is_absolute() else abs_repo / data_yaml
    abs_config_path = Path(config_path) if Path(config_path).is_absolute() else abs_repo / config_path

    # Fallback search for data.yaml if not found
    if not abs_data_yaml.exists():
        expanded_data = abs_repo / "data" / "external" / "rail_defects_expanded" / "data.yaml"
        if expanded_data.exists():
            abs_data_yaml = expanded_data

    # Fallback search for config if not found
    if not abs_config_path.exists():
        custom_cfg = abs_repo / "ml" / "configs" / "yolo_custom_train.yaml"
        if custom_cfg.exists():
            abs_config_path = custom_cfg

    if output_dir:
        abs_output_dir = Path(output_dir) if Path(output_dir).is_absolute() else abs_repo / output_dir
    else:
        abs_output_dir = ModelRegistry.CHECKPOINTS_DIR / "vision"
    abs_output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize and dynamically set path in data.yaml for current OS/environment
    if abs_data_yaml.exists():
        with open(abs_data_yaml, "r", encoding="utf-8") as f:
            dy = yaml.safe_load(f) or {}
        dataset_dir = abs_data_yaml.parent.resolve().as_posix()
        if dy.get("path") != dataset_dir:
            dy["path"] = dataset_dir
            with open(abs_data_yaml, "w", encoding="utf-8") as f:
                yaml.dump(dy, f, sort_keys=False)

    # Load configuration
    cfg = {}
    if abs_config_path.exists():
        with open(abs_config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    train_cfg = cfg.get("training", {})
    aug_cfg = cfg.get("augmentations", {})

    target_device = resolve_device(device if device != "auto" else cfg.get("device", "auto"))

    # Resolve training parameters (CLI overrides config)
    total_epochs = epochs or cfg.get("epochs") or train_cfg.get("epochs", 100)
    batch = batch_size or cfg.get("batch") or train_cfg.get("batch_size", 16)
    imgsz = img_size or cfg.get("imgsz") or cfg.get("model", {}).get("input_size", [640, 640])[0] if isinstance(cfg.get("model", {}).get("input_size"), list) else 640
    optimizer = cfg.get("optimizer") or train_cfg.get("optimizer", "AdamW")
    lr0 = cfg.get("lr0") or train_cfg.get("lr0", 0.0008)
    lrf = cfg.get("lrf") or train_cfg.get("lrf", 0.01)
    cos_lr = cfg.get("cos_lr", train_cfg.get("cos_lr", True))
    patience = cfg.get("patience", train_cfg.get("patience", 40))
    close_mosaic = cfg.get("close_mosaic", train_cfg.get("close_mosaic", 30))

    # Model initialization
    model_name = cfg.get("model", {}).get("name", "yolov8n.pt") if isinstance(cfg.get("model"), dict) else cfg.get("model", "yolov8n.pt")
    base_weights = ModelRegistry.get_base_weights("vision", model_name)
    model_init = str(base_weights) if base_weights.exists() else model_name

    print("=" * 70)
    print("TrackChain YOLOv8n Defect Detector Training")
    print("=" * 70)
    print(f"Dataset YAML: {abs_data_yaml}")
    print(f"Config:       {abs_config_path}")
    print(f"Output Dir:   {abs_output_dir}")
    print(f"Device:       {target_device}")
    print(f"Epochs:       {total_epochs}")
    print(f"Batch Size:   {batch}")
    print(f"Image Size:   {imgsz}")
    print(f"Optimizer:    {optimizer} (lr0={lr0}, cos_lr={cos_lr})")

    model = YOLO(model_init)

    # Register metrics logger callback
    logger = MetricsLogger(abs_output_dir / "logs")
    model.add_callback("on_fit_epoch_end", logger.on_fit_epoch_end)

    # Compose train arguments
    train_args = {
        "data": str(abs_data_yaml),
        "epochs": total_epochs,
        "batch": batch,
        "imgsz": imgsz,
        "device": target_device,
        "optimizer": optimizer,
        "lr0": lr0,
        "lrf": lrf,
        "momentum": cfg.get("momentum", 0.937),
        "weight_decay": cfg.get("weight_decay", train_cfg.get("weight_decay", 0.0005)),
        "cos_lr": cos_lr,
        "warmup_epochs": cfg.get("warmup_epochs", train_cfg.get("warmup_epochs", 3.0)),
        "warmup_momentum": cfg.get("warmup_momentum", 0.8),
        "warmup_bias_lr": cfg.get("warmup_bias_lr", 0.1),
        "box": cfg.get("box", 7.5),
        "cls": cfg.get("cls", 0.5),
        "dfl": cfg.get("dfl", 1.5),
        "hsv_h": cfg.get("hsv_h", aug_cfg.get("hsv_h", 0.015)),
        "hsv_s": cfg.get("hsv_s", aug_cfg.get("hsv_s", 0.7)),
        "hsv_v": cfg.get("hsv_v", aug_cfg.get("hsv_v", 0.4)),
        "degrees": cfg.get("degrees", aug_cfg.get("degrees", 15.0)),
        "translate": cfg.get("translate", aug_cfg.get("translate", 0.2)),
        "scale": cfg.get("scale", aug_cfg.get("scale", 0.7)),
        "shear": cfg.get("shear", aug_cfg.get("shear", 5.0)),
        "perspective": cfg.get("perspective", aug_cfg.get("perspective", 0.001)),
        "flipud": cfg.get("flipud", aug_cfg.get("flipud", 0.5)),
        "fliplr": cfg.get("fliplr", aug_cfg.get("fliplr", 0.5)),
        "mosaic": cfg.get("mosaic", aug_cfg.get("mosaic", 1.0)),
        "mixup": cfg.get("mixup", aug_cfg.get("mixup", 0.15)),
        "copy_paste": cfg.get("copy_paste", aug_cfg.get("copy_paste", 0.3)),
        "close_mosaic": close_mosaic,
        "patience": patience,
        "val": True,
        "conf": cfg.get("conf", 0.001),
        "iou": cfg.get("iou", 0.6),
        "workers": min(cfg.get("workers", 4), os.cpu_count() or 4),
        "pretrained": True,
        "project": str(abs_output_dir),
        "name": run_name,
        "exist_ok": True,
        "verbose": True,
        "plots": True,
        "save": True,
        "save_period": cfg.get("save_period", 10),
        "label_smoothing": cfg.get("label_smoothing", 0.05),
        "rect": cfg.get("rect", False),
    }

    # Remove None items
    train_args = {k: v for k, v in train_args.items() if v is not None}

    print("\n[INFO] Commencing training...")
    start_time = time.time()
    results = model.train(**train_args)
    training_time = time.time() - start_time
    print(f"\n[INFO] Training completed in {training_time/3600:.2f} hours ({training_time:.1f}s)")

    # Canonical checkpoint synchronization
    best_pt = abs_output_dir / run_name / "weights" / "best.pt"
    canonical_best = abs_output_dir / "yolov8n_rail_best.pt"
    alias_best = abs_output_dir / "yolo_rail_v0.1.pt"

    if best_pt.exists():
        shutil.copy(best_pt, canonical_best)
        shutil.copy(best_pt, alias_best)
        print(f"[OK] Checkpoints saved to:\n     {canonical_best}\n     {alias_best}")
    else:
        last_pt = abs_output_dir / run_name / "weights" / "last.pt"
        if last_pt.exists():
            shutil.copy(last_pt, canonical_best)
            shutil.copy(last_pt, alias_best)

    # Validate best model on test split
    final_metrics = {
        "training_time_hours": round(training_time / 3600, 4),
        "training_time_seconds": round(training_time, 2),
        "best_model": str(best_pt if best_pt.exists() else canonical_best),
        "timestamp": datetime.now().isoformat(),
        "device": target_device,
    }

    if canonical_best.exists():
        try:
            best_model = YOLO(str(canonical_best))
            val_results = best_model.val(data=str(abs_data_yaml), split="test")
            final_metrics["test_mAP50"] = float(val_results.box.map50)
            final_metrics["test_mAP50_95"] = float(val_results.box.map)
            final_metrics["test_precision"] = float(val_results.box.mp)
            final_metrics["test_recall"] = float(val_results.box.mr)

            print("\n" + "=" * 70)
            print("Post-Training Test Set Validation Results")
            print("=" * 70)
            print(f"Test mAP50:    {val_results.box.map50:.4f}")
            print(f"Test mAP50-95: {val_results.box.map:.4f}")
            print(f"Test Precision:{val_results.box.mp:.4f}")
            print(f"Test Recall:   {val_results.box.mr:.4f}")
        except Exception as e:
            print(f"[WARN] Test set validation skipped: {e}")

    with open(abs_output_dir / "final_metrics.json", "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, indent=2)

    return results


# Alias for backwards compatibility
train_custom = train_yolo_detector


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train TrackChain YOLOv8n defect detector.")
    parser.add_argument("--data", default="data/external/rail_defects/data.yaml", help="Path to data.yaml")
    parser.add_argument("--config", default="ml/configs/detector.yaml", help="Path to config yaml")
    parser.add_argument("--epochs", type=int, default=None, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=None, help="Batch size")
    parser.add_argument("--device", default="auto", help="Device to train on ('auto', '0' for CUDA GPU, or 'cpu')")
    parser.add_argument("--output-dir", default=None, help="Output directory for checkpoints")
    parser.add_argument("--resume", action="store_true", help="Resume training")
    args = parser.parse_args()

    train_yolo_detector(
        data_yaml=args.data,
        config_path=args.config,
        epochs=args.epochs,
        batch_size=args.batch,
        device=args.device,
        output_dir=args.output_dir,
        resume=args.resume,
    )
