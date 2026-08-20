# Export models to ONNX/TFLite for edge deployment.

import os
import torch
import torch.nn as nn
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("exporters")


def export_torch_to_onnx(
    model: nn.Module,
    dummy_input: torch.Tensor,
    output_path: str,
    input_names: list = ["input"],
    output_names: list = ["output"],
):
    """Export a PyTorch model to ONNX for embedded edge acceleration."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model.eval()
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=input_names,
        output_names=output_names,
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )
    logger.info(f"ONNX export successful: {output_path}")
