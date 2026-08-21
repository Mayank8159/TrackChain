"""
TrackChain Master YOLO Detector Training Module (tc.v1 SOTA).
Standard full-network fine-tuning without backbone freezing.
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


def resolve_device(requested_device: Optional[str] = None) -> str:
    """Resolve compute device: auto-detects CUDA GPU if available."""
    if requested_device and requested_device not in ["auto", "", None]:
        return str(requested_device)
    if torch is not None and torch.cuda.is_available():
        return "0"
    return "cpu"


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
            val_loss = float(metrics_dict.get("val/loss", 0.0))

            now = time.time()
            epoch_time = round(now - self.last_epoch_time, 2)
            self.last_epoch_time = now

            self.metrics["epochs"].append(epoch)
            self.metrics["train_loss"].append(round(loss_val, 4))
            self.metrics["val_loss"].append(round(val_loss, 4))
            self.metrics["mAP50"].append(round(map50, 4))
            self.metrics["mAP50_95"].append(round(map50_95, 4))
            self.metrics["precision"].append(round(precision, 4))
            self.metrics["recall"].append(round(recall, 4))
            self.metrics["lr"].append(lr)
            self.metrics["epoch_time_s"].append(epoch_time)

            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception:
            pass


def train_yolo_detector(
    data_yaml: str = "data/external/rail_defects_expanded/data.yaml",
    config_path: str = "ml/configs/detector.yaml",
    epochs: Optional[int] = None,
    batch_size: Optional[int] = None,
    img_size: Optional[int] = None,
    freeze: Optional[int] = None,
    dropout: Optional[float] = None,
    erasing: Optional[float] = None,
    copy_paste: Optional[float] = None,
    close_mosaic: Optional[int] = None,
    patience: Optional[int] = None,
    conf: Optional[float] = None,
    iou: Optional[float] = None,
    device: Optional[str] = "auto",
    output_dir: Optional[str] = None,
    run_name: str = "yolov8n_rail_run",
    resume: bool = False,
) -> Any:
    """
    Train YOLOv8n defect detector with full network optimization (no backbone freezing).
    """
    if YOLO is None:
        raise RuntimeError("Ultralytics package is required. Install with: pip install ultralytics")

    abs_data_yaml = Path(data_yaml) if Path(data_yaml).is_absolute() else repo_root / data_yaml
    if not abs_data_yaml.exists():
        for candidate in ["data/external/rail_defects_expanded/data.yaml", "data/external/rail_defects/data.yaml"]:
            cand_p = repo_root / candidate
            if cand_p.exists():
                abs_data_yaml = cand_p
                break

    abs_config_path = Path(config_path) if Path(config_path).is_absolute() else repo_root / config_path
    abs_output_dir = Path(output_dir) if output_dir else ModelRegistry.CHECKPOINTS_DIR / "vision"
    abs_output_dir.mkdir(parents=True, exist_ok=True)

    # Load configuration
    cfg = {}
    if abs_config_path.exists():
        with open(abs_config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    train_cfg = cfg.get("training", {})
    aug_cfg = cfg.get("augmentations", {})
    val_cfg = cfg.get("validation", {})

    target_device = resolve_device(device if device != "auto" else cfg.get("device", "auto"))

    # Resolve training parameters
    total_epochs = epochs or cfg.get("epochs") or train_cfg.get("epochs", 50)
    batch = batch_size or cfg.get("batch") or train_cfg.get("batch_size", 16)
    
    if img_size:
        imgsz = img_size
    elif cfg.get("imgsz"):
        imgsz = cfg.get("imgsz")
    elif isinstance(cfg.get("model", {}).get("input_size"), list):
        imgsz = cfg.get("model", {}).get("input_size")[0]
    else:
        imgsz = 640

    optimizer = cfg.get("optimizer") or train_cfg.get("optimizer", "AdamW")
    lr0 = cfg.get("lr0") or train_cfg.get("lr0", 0.0008)
    lrf = cfg.get("lrf") or train_cfg.get("lrf", 0.01)
    cos_lr = cfg.get("cos_lr", train_cfg.get("cos_lr", True))
    
    patience_val = patience if patience is not None else cfg.get("patience", train_cfg.get("patience", 40))
    close_mosaic_val = close_mosaic if close_mosaic is not None else cfg.get("close_mosaic", train_cfg.get("close_mosaic", 30))
    freeze_val = freeze if freeze is not None else cfg.get("freeze", train_cfg.get("freeze", None))
    dropout_val = dropout if dropout is not None else cfg.get("dropout", train_cfg.get("dropout", 0.0))
    erasing_val = erasing if erasing is not None else cfg.get("erasing", train_cfg.get("erasing", 0.4))
    copy_paste_val = copy_paste if copy_paste is not None else cfg.get("copy_paste", aug_cfg.get("copy_paste", 0.3))
    conf_val = conf if conf is not None else cfg.get("conf", val_cfg.get("conf", 0.001))
    iou_val = iou if iou is not None else cfg.get("iou", val_cfg.get("iou", 0.60))

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
        "warmup_epochs": cfg.get("warmup_epochs", train_cfg.get("warmup_epochs", 5.0)),
        "warmup_momentum": cfg.get("warmup_momentum", 0.8),
        "warmup_bias_lr": cfg.get("warmup_bias_lr", 0.1),
        "box": cfg.get("box", 7.5),
        "cls": cfg.get("cls", 0.5),
        "dfl": cfg.get("dfl", 1.5),
        "freeze": freeze_val,
        "dropout": dropout_val,
        "erasing": erasing_val,
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
        "copy_paste": copy_paste_val,
        "close_mosaic": close_mosaic_val,
        "patience": patience_val,
        "val": True,
        "conf": conf_val,
        "iou": iou_val,
        "workers": min(cfg.get("workers", 4), os.cpu_count() or 4),
        "pretrained": True,
        "project": str(abs_output_dir),
        "name": run_name,
        "exist_ok": True,
        "verbose": True,
        "plots": True,
        "save": True,
        "save_period": cfg.get("save_period", 10),
        "rect": cfg.get("rect", False),
        "resume": resume,
    }

    # Remove None items except for freeze when None is intentional
    train_args = {k: v for k, v in train_args.items() if v is not None or k == "freeze"}

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
        "imgsz": imgsz,
        "conf_threshold": conf_val,
        "iou_threshold": iou_val,
    }

    if canonical_best.exists():
        try:
            best_model = YOLO(str(canonical_best))
            val_results = best_model.val(data=str(abs_data_yaml), split="test", conf=conf_val, iou=iou_val)
            final_metrics["test_mAP50"] = float(val_results.box.map50)
            final_metrics["test_mAP50_95"] = float(val_results.box.map)
            final_metrics["test_precision"] = float(val_results.box.mp)
            final_metrics["test_recall"] = float(val_results.box.mr)

            print("\n" + "=" * 75)
            print(f"Post-Training Test Set Validation Results (conf={conf_val})")
            print("=" * 75)
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
    parser.add_argument("--data", default="data/external/rail_defects_expanded/data.yaml", help="Path to data.yaml")
    parser.add_argument("--config", default="ml/configs/detector.yaml", help="Path to config yaml")
    parser.add_argument("--epochs", type=int, default=None, help="Number of training epochs (default 50)")
    parser.add_argument("--batch", type=int, default=None, help="Batch size (default 16)")
    parser.add_argument("--imgsz", type=int, default=None, help="Input resolution (default 640)")
    parser.add_argument("--freeze", type=int, default=None, help="Number of backbone layers to freeze (default None)")
    parser.add_argument("--dropout", type=float, default=None, help="Dropout regularization rate (default 0.0)")
    parser.add_argument("--erasing", type=float, default=None, help="Random erasing probability (default 0.4)")
    parser.add_argument("--copy-paste", type=float, default=None, help="Copy-paste augmentation rate (default 0.3)")
    parser.add_argument("--close-mosaic", type=int, default=None, help="Epochs before end to disable mosaic (default 30)")
    parser.add_argument("--patience", type=int, default=None, help="Early stopping patience (default 40)")
    parser.add_argument("--conf", type=float, default=None, help="Validation confidence threshold (default 0.001)")
    parser.add_argument("--iou", type=float, default=None, help="NMS IoU threshold (default 0.60)")
    parser.add_argument("--device", default="auto", help="Device to train on ('auto', '0' for CUDA GPU, or 'cpu')")
    parser.add_argument("--output-dir", default=None, help="Output directory for checkpoints")
    parser.add_argument("--resume", action="store_true", help="Resume training from last checkpoint")
    args = parser.parse_args()

    train_yolo_detector(
        data_yaml=args.data,
        config_path=args.config,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.imgsz,
        freeze=args.freeze,
        dropout=args.dropout,
        erasing=args.erasing,
        copy_paste=args.copy_paste,
        close_mosaic=args.close_mosaic,
        patience=args.patience,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        output_dir=args.output_dir,
        resume=args.resume,
    )
