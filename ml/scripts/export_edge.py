# Export calibrated models for the edge device.

import torch
from ml.models.geometry.fault_classifier import BiLSTMGeometryClassifier
from ml.inference.exporters import export_torch_to_onnx
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("export_edge")


def main():
    logger.info("Exporting calibrated models for embedded edge inference...")
    model = BiLSTMGeometryClassifier(input_dim=6, num_classes=4)
    dummy_input = torch.randn(1, 100, 6)

    export_torch_to_onnx(
        model=model,
        dummy_input=dummy_input,
        output_path="artifacts/exports/geometry_classifier.onnx",
    )
    logger.info("Edge export completed.")


if __name__ == "__main__":
    main()
