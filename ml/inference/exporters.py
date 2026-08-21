"""
ml/inference/exporters.py
Export PyTorch weights to ONNX and INT8 quantized runtime for edge deployment (tc.v1 SOTA).
Optimized for cross-platform execution on edge compute devices (NVIDIA Jetson, ARM, x86 TRC edge nodes).
"""

import argparse
import os
import sys
import shutil
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


def export_yolo_to_onnx(
    model_path: str,
    output_dir: str = "artifacts/exports",
    img_size: int = 640,
    opset: int = 12,
    simplify: bool = True,
    dynamic: bool = False,
) -> str:
    """
    Export a trained YOLOv8 model (.pt) to high-performance ONNX format.
    """
    if YOLO is None:
        raise RuntimeError("Ultralytics is required for model export. Install with: pip install ultralytics")

    abs_model_path = Path(model_path) if Path(model_path).is_absolute() else repo_root / model_path
    if not abs_model_path.exists():
        candidates = [
            repo_root / "artifacts" / "checkpoints" / "vision" / "yolov8n_rail_best.pt",
            repo_root / "artifacts" / "checkpoints" / "vision" / "yolov8n_rail_run" / "weights" / "best.pt",
            repo_root / "artifacts" / "checkpoints" / "yolov8n_rail_best.pt",
            repo_root / "yolov8n.pt",
        ]
        for c in candidates:
            if c.exists():
                abs_model_path = c
                break

    if not abs_model_path.exists():
        raise FileNotFoundError(f"Model weights not found at: {abs_model_path}")

    abs_output_dir = Path(output_dir) if Path(output_dir).is_absolute() else repo_root / output_dir
    abs_output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Exporting {abs_model_path} to ONNX (imgsz={img_size}, opset={opset}, simplify={simplify})...")
    model = YOLO(str(abs_model_path))
    exported_file = model.export(
        format="onnx",
        imgsz=img_size,
        opset=opset,
        simplify=simplify,
        dynamic=dynamic,
    )

    # Canonical target path
    target_onnx = abs_output_dir / (abs_model_path.stem + ".onnx")
    if Path(exported_file).resolve() != target_onnx.resolve():
        shutil.copy2(str(exported_file), str(target_onnx))

    print(f"[OK] Successfully exported ONNX model to: {target_onnx}")
    return str(target_onnx)


def quantize_onnx_int8(
    onnx_model_path: str,
    output_quantized_path: Optional[str] = None,
    output_dir: str = "artifacts/exports",
) -> str:
    """
    Apply dynamic INT8 quantization to an ONNX model.
    Shrinks model file size by ~4x and speeds up inference by ~3x on CPU / edge runtimes.
    """
    abs_onnx = Path(onnx_model_path) if Path(onnx_model_path).is_absolute() else repo_root / onnx_model_path
    abs_output_dir = Path(output_dir) if Path(output_dir).is_absolute() else repo_root / output_dir
    abs_output_dir.mkdir(parents=True, exist_ok=True)

    if output_quantized_path is None:
        target_int8 = abs_output_dir / f"{abs_onnx.stem}_int8{abs_onnx.suffix}"
    else:
        target_int8 = Path(output_quantized_path) if Path(output_quantized_path).is_absolute() else repo_root / output_quantized_path

    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
    except ImportError:
        print("[WARN] onnxruntime.quantization not available. Copying ONNX model as fallback.")
        shutil.copy2(str(abs_onnx), str(target_int8))
        return str(target_int8)

    print(f"[INFO] Quantizing {abs_onnx} to INT8 dynamic runtime...")
    quantize_dynamic(
        model_input=str(abs_onnx),
        model_output=str(target_int8),
        weight_type=QuantType.QUInt8,
    )
    print(f"[OK] Saved INT8 quantized edge model: {target_int8}")
    return str(target_int8)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YOLO models to edge ONNX / INT8 runtimes.")
    parser.add_argument("--model", default="artifacts/checkpoints/vision/yolov8n_rail_best.pt", help="Path to .pt weights")
    parser.add_argument("--format", choices=["onnx", "int8", "all"], default="onnx", help="Export target format")
    parser.add_argument("--outdir", default="artifacts/exports", help="Export destination directory")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution for export")
    args = parser.parse_args()

    model_path = args.model
    if not os.path.exists(model_path):
        candidates = [
            os.path.join("artifacts", "checkpoints", "vision", "yolov8n_rail_best.pt"),
            os.path.join("artifacts", "checkpoints", "vision", "yolov8n_rail_run", "weights", "best.pt"),
            os.path.join("artifacts", "checkpoints", "yolov8n_rail_best.pt"),
            "yolov8n.pt",
        ]
        for c in candidates:
            if os.path.exists(c):
                model_path = c
                break

    if args.format in ["onnx", "all"]:
        onnx_file = export_yolo_to_onnx(model_path, output_dir=args.outdir, img_size=args.imgsz)
        if args.format == "all" or args.format == "int8":
            quantize_onnx_int8(onnx_file, output_dir=args.outdir)
    elif args.format == "int8":
        base_onnx = str(Path(args.outdir) / (Path(model_path).stem + ".onnx"))
        if not os.path.exists(base_onnx):
            base_onnx = export_yolo_to_onnx(model_path, output_dir=args.outdir, img_size=args.imgsz)
        quantize_onnx_int8(base_onnx, output_dir=args.outdir)
