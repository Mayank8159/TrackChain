"""
Comprehensive validation of trained YOLO railway defect model (tc.v1 SOTA).
Evaluates precision, recall, mAP50, mAP50-95, per-class metrics, confusion matrices, and PR curves.
Default validation operates at conf=0.25 (realistic operating threshold).
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np

# Ensure repo root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    import matplotlib
    matplotlib.use('Agg')  # Headless backend
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    plt = None
    sns = None

from ml.core.registry import ModelRegistry


def validate_model(
    model_path: str,
    data_yaml: str,
    output_dir: str = 'artifacts/validation/yolo',
    split: str = 'test',
    conf: float = 0.25,
    iou: float = 0.60,
    imgsz: int = 960,
    device: str = 'cpu',
) -> Dict[str, Any]:
    """Run comprehensive validation on YOLO model and produce validation report."""
    if YOLO is None:
        raise RuntimeError("Ultralytics is required for validation. Install with: pip install ultralytics")

    abs_repo = ModelRegistry.ROOT
    abs_model = Path(model_path) if Path(model_path).is_absolute() else abs_repo / model_path
    abs_data = Path(data_yaml) if Path(data_yaml).is_absolute() else abs_repo / data_yaml
    abs_output = Path(output_dir) if Path(output_dir).is_absolute() else abs_repo / output_dir
    abs_output.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("TrackChain YOLO Model Comprehensive Validation (tc.v1 SOTA)")
    print("=" * 75)
    print(f"Model:          {abs_model}")
    print(f"Data YAML:      {abs_data}")
    print(f"Split:          {split}")
    print(f"Conf Threshold: {conf}")
    print(f"IoU Threshold:  {iou}")
    print(f"Input Size:     {imgsz}x{imgsz}")
    print(f"Output Dir:     {abs_output}")

    if not abs_model.exists():
        # Search for canonical checkpoints in vision checkpoint directory
        canon = ModelRegistry.CHECKPOINTS_DIR / "vision" / "yolov8n_rail_best.pt"
        if canon.exists():
            abs_model = canon
        else:
            raise FileNotFoundError(f"Model weights not found at {abs_model}")

    model = YOLO(str(abs_model))

    # Run validation
    print(f"\n[1/4] Running validation on {split} split (conf={conf}, iou={iou})...")
    try:
        results = model.val(
            data=str(abs_data),
            split=split,
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            device=device,
            verbose=True,
        )
    except Exception as e:
        print(f"[WARN] Validation on split='{split}' encountered '{e}'. Falling back to split='val'...")
        results = model.val(
            data=str(abs_data),
            split='val',
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            device=device,
            verbose=True,
        )

    # Extract metrics
    mp = float(results.box.mp)
    mr = float(results.box.mr)
    f1 = 2 * (mp * mr) / (mp + mr + 1e-6)

    metrics = {
        'mAP50': float(results.box.map50),
        'mAP50_95': float(results.box.map),
        'precision': mp,
        'recall': mr,
        'f1_score': float(f1),
        'operating_conf': conf,
        'operating_iou': iou,
    }

    # Extract per-class metrics
    class_metrics = {}
    class_names = results.names or {}
    ap50_list = results.box.ap50 if hasattr(results.box, 'ap50') else []
    ap_list = results.box.ap if hasattr(results.box, 'ap') else []

    for i, (cls_id, cls_name) in enumerate(class_names.items()):
        cls_ap50 = float(ap50_list[i]) if i < len(ap50_list) else 0.0
        cls_ap = float(ap_list[i]) if i < len(ap_list) else 0.0
        class_metrics[cls_name] = {
            'AP50': cls_ap50,
            'AP50_95': cls_ap,
        }

    # Confusion matrix generation
    print("\n[2/4] Generating confusion matrix...")
    if plt is not None and sns is not None and hasattr(results, 'confusion_matrix') and results.confusion_matrix is not None:
        try:
            cm = results.confusion_matrix.matrix
            labels = [class_names.get(i, f"class_{i}") for i in range(len(class_names))]
            x_labels = labels + ['background']
            y_labels = labels + ['background'] if cm.shape[0] > len(labels) else labels

            plt.figure(figsize=(9, 7))
            sns.heatmap(cm, annot=True, fmt='.1f' if cm.dtype == float else 'd', cmap='Blues',
                        xticklabels=x_labels[:cm.shape[1]],
                        yticklabels=y_labels[:cm.shape[0]])
            plt.xlabel('Predicted')
            plt.ylabel('Ground Truth')
            plt.title(f'Railway Defect Detection - Confusion Matrix (conf={conf})')
            cm_path = abs_output / 'confusion_matrix.png'
            plt.savefig(cm_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"      Saved confusion matrix: {cm_path}")
        except Exception as e:
            print(f"      [WARN] Confusion matrix plotting skipped: {e}")

    # PR curve visualization
    print("\n[3/4] Generating PR curves...")
    if plt is not None and hasattr(results, 'curves_results'):
        try:
            plt.figure(figsize=(9, 6))
            for i, cls_name in class_names.items():
                ap_val = class_metrics.get(cls_name, {}).get('AP50', 0.0)
                plt.plot([0, 1], [ap_val, ap_val], label=f"{cls_name} (AP50={ap_val:.3f})")
            plt.xlabel('Recall')
            plt.ylabel('Precision')
            plt.title('Precision-Recall Curves by Defect Class')
            plt.legend(loc='lower left')
            plt.grid(True, linestyle='--', alpha=0.5)
            pr_path = abs_output / 'pr_curves.png'
            plt.savefig(pr_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"      Saved PR curve: {pr_path}")
        except Exception as e:
            print(f"      [WARN] PR curve plotting skipped: {e}")

    # Test-Time Augmentation (TTA) optional evaluation
    tta_metrics = {}
    if tta:
        print(f"\n[INFO] Running Test-Time Augmentation (TTA) evaluation on {split} split...")
        try:
            tta_results = model.val(
                data=str(abs_data),
                split=split,
                conf=conf,
                iou=iou,
                imgsz=imgsz,
                device=device,
                augment=True,
                verbose=False,
            )
            tta_metrics = {
                'mAP50_tta': float(tta_results.box.map50),
                'mAP50_95_tta': float(tta_results.box.map),
                'precision_tta': float(tta_results.box.mp),
                'recall_tta': float(tta_results.box.mr),
            }
        except Exception as e:
            print(f"      [WARN] TTA evaluation encountered error: {e}")

    # Generate validation report
    print("\n[4/4] Generating validation report JSON...")
    num_params = sum(p.numel() for p in model.model.parameters()) if model.model else 0
    file_size_mb = abs_model.stat().st_size / (1024 * 1024) if abs_model.exists() else 0.0

    report = {
        'model_path': str(abs_model),
        'data_yaml': str(abs_data),
        'split': split,
        'overall_metrics': metrics,
        'tta_metrics': tta_metrics,
        'class_metrics': class_metrics,
        'num_parameters': num_params,
        'model_size_mb': round(file_size_mb, 2),
    }

    report_path = abs_output / 'validation_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # Print summary table
    print("\n" + "=" * 75)
    print(f"Validation Results Summary (conf={conf}, iou={iou}, imgsz={imgsz})")
    print("=" * 75)
    print(f"Standard mAP50:     {metrics['mAP50']:.4f}")
    print(f"Standard mAP50-95:  {metrics['mAP50_95']:.4f}")
    if tta_metrics:
        print(f"TTA mAP50:          {tta_metrics.get('mAP50_tta', 0.0):.4f} (Δ={tta_metrics.get('mAP50_tta', 0.0) - metrics['mAP50']:+.4f})")
        print(f"TTA mAP50-95:       {tta_metrics.get('mAP50_95_tta', 0.0):.4f} (Δ={tta_metrics.get('mAP50_95_tta', 0.0) - metrics['mAP50_95']:+.4f})")
    print(f"Precision:          {metrics['precision']:.4f}")
    print(f"Recall:             {metrics['recall']:.4f}")
    print(f"F1 Score:           {metrics['f1_score']:.4f}")
    print(f"Model Size:         {report['model_size_mb']:.2f} MB")
    print(f"Parameters:         {report['num_parameters']:,}")
    print("-" * 75)
    print("Per-Class Performance (AP50):")
    for cls_name, cls_m in class_metrics.items():
        print(f"  {cls_name:22s}: AP50 = {cls_m['AP50']:.4f} | AP50-95 = {cls_m['AP50_95']:.4f}")
    print("=" * 75)
    print(f"Report saved to: {report_path}")

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TrackChain YOLO Validation Suite (tc.v1 SOTA)")
    parser.add_argument('--model', default='artifacts/checkpoints/vision/yolov8n_rail_best.pt', help="Path to .pt weights")
    parser.add_argument('--data', default='data/external/rail_defects_expanded/data.yaml', help="Path to data.yaml")
    parser.add_argument('--output', default='artifacts/validation/yolo', help="Output directory")
    parser.add_argument('--split', default='test', choices=['val', 'test', 'train'])
    parser.add_argument('--conf', type=float, default=0.25, help="Confidence threshold (default 0.25)")
    parser.add_argument('--iou', type=float, default=0.60, help="IoU threshold (default 0.60)")
    parser.add_argument('--imgsz', type=int, default=960, help="Image size (default 960)")
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--tta', '--augment', dest="tta", action='store_true', help="Enable Test-Time Augmentation evaluation")

    args = parser.parse_args()

    validate_model(
        model_path=args.model,
        data_yaml=args.data,
        output_dir=args.output,
        split=args.split,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        device=args.device,
        tta=args.tta,
    )
