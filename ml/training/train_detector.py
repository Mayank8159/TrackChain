"""
ml/training/train_detector.py
Fine-tune the YOLOv8 defect detector on railway defect imagery (tc.v1 SOTA).
Full network fine-tuning without backbone freezing.
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.scripts.train_detector import train_yolo_detector

__all__ = ["train_yolo_detector"]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train YOLOv8 defect detector.")
    parser.add_argument("--data", default="data/external/rail_defects_expanded/data.yaml", help="Path to data.yaml")
    parser.add_argument("--config", default="ml/configs/detector.yaml", help="Path to detector.yaml")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--freeze", type=int, default=None, help="Backbone freeze layers (default None)")
    parser.add_argument("--dropout", type=float, default=0.0, help="Dropout rate")
    parser.add_argument("--erasing", type=float, default=0.4, help="Random erasing rate")
    parser.add_argument("--device", default="auto", help="Device ('auto', '0' for CUDA GPU, or 'cpu')")
    parser.add_argument("--output-dir", default=None, help="Output directory for checkpoints")
    parser.add_argument("--resume", action="store_true", help="Resume training")
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
        device=args.device,
        output_dir=args.output_dir,
        resume=args.resume,
    )
