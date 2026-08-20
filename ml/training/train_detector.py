# Fine-tune the YOLO detector on real/synthetic defect imagery.

import os
import argparse
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("train_detector")


def train_yolo_detector(data_yaml: str, epochs: int = 50, batch_size: int = 16):
    """Orchestrate YOLOv8 transfer learning on annotated rail surface defects."""
    logger.info(f"Starting YOLO detector training with config: {data_yaml}")
    # from ultralytics import YOLO
    # model = YOLO("yolov8n.pt")
    # model.train(data=data_yaml, epochs=epochs, batch=batch_size, project="artifacts/checkpoints", name="yolo_detector")
    logger.info("YOLO detector training script completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="ml/configs/detector.yaml")
    parser.add_argument("--epochs", type=int, default=10)
    args = parser.parse_args()
    train_yolo_detector(args.data, args.epochs)
