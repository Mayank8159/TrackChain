"""
TrackChain Master YOLO Detector Training Module (tc.v1 SOTA).
Comprehensive training pipeline with:
- Manifest fingerprinting & smart skip logic (config_hash, dataset_hash, min metric gates)
- Upgraded small-dataset anti-overfitting recipe (backbone freeze=10, dropout=0.1, erasing=0.2)
- High-impact augmentation schedule (close_mosaic=10, copy_paste=0.5, mixup=0.15, mosaic=1.0)
- High-resolution small-object sensitivity (imgsz=960 for fasteners/clips/cracks)
- Test-Time Augmentation (TTA) evaluation on test split
- Realistic operating validation threshold (conf=0.25, iou=0.60)
- MetricsLogger callback tracking loss, mAP50, mAP50-95, precision, recall, and learning rate
- Automatic device resolution (CUDA GPU auto-detection with CPU fallback)
- Canonical checkpoint synchronization with ModelRegistry
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
from ml.core.manifest import (
    compute_config_hash,
    compute_dataset_hash,
    check_training_skip,
    save_manifest,
)


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

            loss_val = 0.0
            if hasattr(trainer, "loss_items") and trainer.loss_items is not None:
                loss_val = float(trainer.loss_items.mean().item())
            elif hasattr(trainer, "loss") and trainer.loss is not None:
                loss_val = float(trainer.loss.item())

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
    img_size: Optional[int] = 960,
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
    force: bool = False,
    min_map50_gate: float = 0.25,
) -> Any:
    """
    Train YOLOv8n defect detector with manifest skip-logic, SOTA recipe, and TTA evaluation.
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
    model_cfg = cfg.get("model", {})

    total_epochs = epochs if epochs is not None else cfg.get("epochs", train_cfg.get("epochs", 80))
    batch = batch_size if batch_size is not None else cfg.get("batch_size", train_cfg.get("batch_size", 8))
    imgsz = img_size if img_size is not None else (model_cfg.get("input_size", [960, 960])[0] if isinstance(model_cfg.get("input_size"), list) else 960)
    target_device = resolve_device(device if device is not None else cfg.get("device", "auto"))

    patience_val = patience if patience is not None else cfg.get("patience", train_cfg.get("patience", 20))
    close_mosaic_val = close_mosaic if close_mosaic is not None else cfg.get("close_mosaic", train_cfg.get("close_mosaic", 10))
    freeze_val = freeze if freeze is not None else cfg.get("freeze", train_cfg.get("freeze", 10))
    dropout_val = dropout if dropout is not None else cfg.get("dropout", train_cfg.get("dropout", 0.1))
    erasing_val = erasing if erasing is not None else cfg.get("erasing", train_cfg.get("erasing", 0.2))
    copy_paste_val = copy_paste if copy_paste is not None else cfg.get("copy_paste", aug_cfg.get("copy_paste", 0.5))
    conf_val = conf if conf is not None else cfg.get("conf", val_cfg.get("conf", 0.25))
    iou_val = iou if iou is not None else cfg.get("iou", val_cfg.get("iou", 0.60))

    # Compute config and dataset fingerprints
    overrides_dict = {
        "epochs": total_epochs,
        "batch": batch,
        "imgsz": imgsz,
        "freeze": freeze_val,
        "dropout": dropout_val,
        "erasing": erasing_val,
        "close_mosaic": close_mosaic_val,
    }
    current_config_hash = compute_config_hash(abs_config_path, overrides=overrides_dict)
    current_dataset_hash = compute_dataset_hash(abs_data_yaml)

    canonical_best = abs_output_dir / "yolov8n_rail_best.pt"
    manifest_file = abs_output_dir / "yolo_manifest.json"

    # Check manifest skip-logic
    if not force and canonical_best.exists():
        should_skip, skip_reason = check_training_skip(
            manifest_path=manifest_file,
            checkpoint_path=canonical_best,
            current_config_hash=current_config_hash,
            current_dataset_hash=current_dataset_hash,
            min_metrics={"mAP50": min_map50_gate},
            force=force,
        )
        if should_skip:
            print("=" * 75)
            print("TrackChain YOLOv8n Training Skipped (Manifest Match)")
            print("=" * 75)
            print(f"[SKIP] {skip_reason}")
            print(f"       Checkpoint: {canonical_best}")
            print(f"       Manifest:   {manifest_file}")
            print("=" * 75)
            return None

    # Model initialization
    model_name = model_cfg.get("name", "yolov8n.pt") if isinstance(model_cfg, dict) else "yolov8n.pt"
    base_weights = ModelRegistry.get_base_weights("vision", model_name)
    model_init = str(base_weights) if base_weights.exists() else model_name

    print("=" * 75)
    print("TrackChain Upgraded YOLOv8n Defect Detector Training (tc.v1 SOTA)")
    print("=" * 75)
    print(f"Dataset YAML:  {abs_data_yaml}")
    print(f"Config Hash:   {current_config_hash[:12]}...")
    print(f"Dataset Hash:  {current_dataset_hash[:12]}...")
    print(f"Image Size:    {imgsz}x{imgsz} (High resolution small-object sensitivity)")
    print(f"Epochs:        {total_epochs} (Close mosaic: {close_mosaic_val}, Freeze: {freeze_val})")
    print(f"Batch Size:    {batch}")
    print(f"Device:        {target_device}")
    print(f"Dropout / Era: {dropout_val} / {erasing_val}")
    print(f"Val Conf / IoU:{conf_val} / {iou_val}")

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
        "optimizer": cfg.get("optimizer", train_cfg.get("optimizer", "AdamW")),
        "lr0": cfg.get("lr0", train_cfg.get("lr0", 0.001)),
        "lrf": cfg.get("lrf", train_cfg.get("lrf", 0.01)),
        "momentum": cfg.get("momentum", 0.937),
        "weight_decay": cfg.get("weight_decay", train_cfg.get("weight_decay", 0.0005)),
        "cos_lr": cfg.get("cos_lr", train_cfg.get("cos_lr", True)),
        "warmup_epochs": cfg.get("warmup_epochs", train_cfg.get("warmup_epochs", 3.0)),
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

    train_args = {k: v for k, v in train_args.items() if v is not None}

    print("\n[INFO] Commencing YOLOv8n training...")
    start_time = time.time()
    results = model.train(**train_args)
    training_time = time.time() - start_time
    print(f"\n[INFO] Training completed in {training_time/3600:.2f} hours ({training_time:.1f}s)")

    # Canonical checkpoint synchronization
    best_pt = abs_output_dir / run_name / "weights" / "best.pt"
    alias_best = abs_output_dir / "yolo_rail_v0.1.pt"

    if best_pt.exists():
        shutil.copy(best_pt, canonical_best)
        shutil.copy(best_pt, alias_best)
        print(f"[OK] Checkpoints synchronized:\n     {canonical_best}\n     {alias_best}")

    # Standard and TTA evaluation on test split
    final_metrics: Dict[str, Any] = {
        "training_time_hours": round(training_time / 3600, 4),
        "training_time_seconds": round(training_time, 2),
        "best_model": str(canonical_best),
        "timestamp": datetime.now().isoformat(),
        "device": target_device,
        "imgsz": imgsz,
        "conf_threshold": conf_val,
        "iou_threshold": iou_val,
    }

    if canonical_best.exists():
        try:
            eval_model = YOLO(str(canonical_best))

            # 1. Standard test split validation
            print(f"\n[INFO] Running standard validation on test split (imgsz={imgsz}, conf={conf_val})...")
            std_results = eval_model.val(
                data=str(abs_data_yaml),
                split="test",
                conf=conf_val,
                iou=iou_val,
                imgsz=imgsz,
                augment=False,
            )
            final_metrics["test_mAP50"] = float(std_results.box.map50)
            final_metrics["test_mAP50_95"] = float(std_results.box.map)
            final_metrics["test_precision"] = float(std_results.box.mp)
            final_metrics["test_recall"] = float(std_results.box.mr)

            # 2. Test-Time Augmentation (TTA) validation
            print(f"[INFO] Running Test-Time Augmentation (TTA) validation...")
            try:
                tta_results = eval_model.val(
                    data=str(abs_data_yaml),
                    split="test",
                    conf=conf_val,
                    iou=iou_val,
                    imgsz=imgsz,
                    augment=True,
                )
                final_metrics["test_mAP50_tta"] = float(tta_results.box.map50)
                final_metrics["test_mAP50_95_tta"] = float(tta_results.box.map)
            except Exception as tta_err:
                print(f"[WARN] TTA evaluation skipped: {tta_err}")

            print("\n" + "=" * 75)
            print("Post-Training Test Set Validation & TTA Results")
            print("=" * 75)
            print(f"Standard Test mAP50:     {final_metrics.get('test_mAP50', 0.0):.4f}")
            print(f"Standard Test mAP50-95:  {final_metrics.get('test_mAP50_95', 0.0):.4f}")
            if "test_mAP50_tta" in final_metrics:
                print(f"TTA Test mAP50:          {final_metrics['test_mAP50_tta']:.4f}")
                print(f"TTA Test mAP50-95:       {final_metrics['test_mAP50_95_tta']:.4f}")
            print("=" * 75)
        except Exception as e:
            print(f"[WARN] Post-training validation encountered error: {e}")

    with open(abs_output_dir / "final_metrics.json", "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, indent=2)

    # Save manifest for verified skip logic
    manifest_data = {
        "model": "yolov8n_rail_defect_detector",
        "config_hash": current_config_hash,
        "dataset_hash": current_dataset_hash,
        "hyperparameters": overrides_dict,
        "metrics": {
            "mAP50": final_metrics.get("test_mAP50", 0.0),
            "mAP50_95": final_metrics.get("test_mAP50_95", 0.0),
            "mAP50_tta": final_metrics.get("test_mAP50_tta", final_metrics.get("test_mAP50", 0.0)),
            "precision": final_metrics.get("test_precision", 0.0),
            "recall": final_metrics.get("test_recall", 0.0),
        },
        "weights_path": str(canonical_best),
        "timestamp": datetime.now().isoformat(),
    }
    save_manifest(manifest_file, manifest_data)
    print(f"[OK] Saved verified training manifest to: {manifest_file}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train TrackChain YOLOv8n defect detector (tc.v1 SOTA).")
    parser.add_argument("--data", default="data/external/rail_defects_expanded/data.yaml", help="Path to data.yaml")
    parser.add_argument("--config", default="ml/configs/detector.yaml", help="Path to config yaml")
    parser.add_argument("--epochs", type=int, default=None, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=None, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=960, help="Input resolution (default 960)")
    parser.add_argument("--freeze", type=int, default=None, help="Number of backbone layers to freeze")
    parser.add_argument("--dropout", type=float, default=None, help="Dropout rate")
    parser.add_argument("--erasing", type=float, default=None, help="Random erasing rate")
    parser.add_argument("--copy-paste", type=float, default=None, help="Copy-paste augmentation rate")
    parser.add_argument("--close-mosaic", type=int, default=None, help="Epochs before end to disable mosaic")
    parser.add_argument("--patience", type=int, default=None, help="Early stopping patience")
    parser.add_argument("--conf", type=float, default=None, help="Validation confidence threshold")
    parser.add_argument("--iou", type=float, default=None, help="NMS IoU threshold")
    parser.add_argument("--device", default="auto", help="Device to train on ('auto', '0' for CUDA GPU, or 'cpu')")
    parser.add_argument("--output-dir", default=None, help="Output directory for checkpoints")
    parser.add_argument("--resume", action="store_true", help="Resume training from last checkpoint")
    parser.add_argument("--force", "--force-retrain", dest="force", action="store_true", help="Force retrain and bypass manifest check")
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
        force=args.force,
    )
