"""
ml/training/train_detector.py
Fine-tune the YOLOv8 defect detector on railway defect imagery (tc.v1 SOTA).
"""

from ml.scripts.train_detector import train_yolo_detector

__all__ = ["train_yolo_detector"]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train YOLOv8 defect detector.")
    parser.add_argument("--data", default="data/external/rail_defects/data.yaml", help="Path to data.yaml")
    parser.add_argument("--config", default="ml/configs/detector.yaml", help="Path to detector.yaml")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--device", default="cpu", help="Device ('cpu' or 'cuda')")
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
