# Export PyTorch weights to ONNX and INT8 quantized runtime for edge deployment (tc.v1 SOTA).
# Features cryptographic manifest skip-logic based on source .pt weight hashes.

import argparse
import os
import sys
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from ml.core.manifest import (
    compute_file_sha256,
    check_export_skip,
    load_manifest,
    save_manifest,
)


def export_yolo_to_onnx(
    model_path: str,
    output_dir: str = "artifacts/exports",
    img_size: int = 960,
    opset: int = 12,
    simplify: bool = True,
    dynamic: bool = False,
    force: bool = False,
) -> str:
    """
    Export a trained YOLOv8 model (.pt) to high-performance ONNX format with manifest skip-logic.
    """
    if YOLO is None:
        raise RuntimeError("Ultralytics is required for model export.")

    abs_model_path = Path(model_path) if Path(model_path).is_absolute() else repo_root / model_path
    abs_output_dir = Path(output_dir) if Path(output_dir).is_absolute() else repo_root / output_dir
    abs_output_dir.mkdir(parents=True, exist_ok=True)

    target_onnx = abs_output_dir / (abs_model_path.stem + ".onnx")
    manifest_p = abs_output_dir / "export_manifest.json"

    if not force:
        should_skip, skip_reason = check_export_skip(
            manifest_path=manifest_p,
            export_path=target_onnx,
            source_model_path=abs_model_path,
            export_format="onnx",
            force=force,
        )
        if should_skip:
            print(f"[SKIP] ONNX Export: {skip_reason} ({target_onnx})")
            return str(target_onnx)

    print(f"[INFO] Exporting {abs_model_path} to ONNX (imgsz={img_size}, opset={opset}, simplify={simplify})...")
    model = YOLO(str(abs_model_path))
    exported_file = model.export(
        format="onnx",
        imgsz=img_size,
        opset=opset,
        simplify=simplify,
        dynamic=dynamic,
    )

    if Path(exported_file) != target_onnx:
        shutil.move(exported_file, target_onnx)

    # Update manifest
    manifest_data = load_manifest(manifest_p)
    manifest_data["onnx"] = {
        "source_model": str(abs_model_path),
        "source_model_hash": compute_file_sha256(abs_model_path),
        "export_path": str(target_onnx),
        "imgsz": img_size,
        "opset": opset,
        "timestamp": datetime.now().isoformat(),
    }
    save_manifest(manifest_p, manifest_data)

    print(f"[OK] Successfully exported ONNX model to: {target_onnx}")
    return str(target_onnx)


def quantize_onnx_int8(
    onnx_model_path: str,
    output_quantized_path: Optional[str] = None,
    force: bool = False,
) -> str:
    """
    Apply dynamic INT8 quantization to an ONNX model with manifest skip-logic.
    """
    abs_onnx = Path(onnx_model_path) if Path(onnx_model_path).is_absolute() else repo_root / onnx_model_path
    if output_quantized_path is None:
        target_int8 = abs_onnx.parent / f"{abs_onnx.stem}_int8{abs_onnx.suffix}"
    else:
        target_int8 = Path(output_quantized_path) if Path(output_quantized_path).is_absolute() else repo_root / output_quantized_path

    manifest_p = abs_onnx.parent / "export_manifest.json"

    if not force:
        should_skip, skip_reason = check_export_skip(
            manifest_path=manifest_p,
            export_path=target_int8,
            source_model_path=abs_onnx,
            export_format="int8",
            force=force,
        )
        if should_skip:
            print(f"[SKIP] INT8 Quantization: {skip_reason} ({target_int8})")
            return str(target_int8)

    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
    except ImportError:
        print("[WARN] onnxruntime.quantization not available. Copying ONNX model as fallback.")
        shutil.copy(abs_onnx, target_int8)
        return str(target_int8)

    print(f"[INFO] Quantizing {abs_onnx} to INT8 dynamic runtime...")
    quantize_dynamic(
        model_input=str(abs_onnx),
        model_output=str(target_int8),
        weight_type=QuantType.QUInt8,
    )

    # Update manifest
    manifest_data = load_manifest(manifest_p)
    manifest_data["int8"] = {
        "source_model": str(abs_onnx),
        "source_model_hash": compute_file_sha256(abs_onnx),
        "export_path": str(target_int8),
        "timestamp": datetime.now().isoformat(),
    }
    save_manifest(manifest_p, manifest_data)

    print(f"[OK] Saved INT8 quantized edge model: {target_int8}")
    return str(target_int8)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YOLO models to edge ONNX / INT8 runtimes with manifest skip-logic.")
    parser.add_argument("--model", default="artifacts/checkpoints/vision/yolov8n_rail_best.pt", help="Path to .pt weights")
    parser.add_argument("--format", choices=["onnx", "int8", "all"], default="onnx", help="Export target format")
    parser.add_argument("--outdir", default="artifacts/exports", help="Export destination directory")
    parser.add_argument("--imgsz", type=int, default=960, help="Image resolution for export")
    parser.add_argument("--force", action="store_true", help="Force re-export and bypass manifest")
    args = parser.parse_args()

    model_path = args.model
    if not os.path.exists(model_path):
        candidates = [
            os.path.join("artifacts", "checkpoints", "vision", "yolov8n_rail_best.pt"),
            os.path.join("artifacts", "checkpoints", "vision", "yolov8n_rail_custom", "weights", "best.pt"),
            os.path.join("artifacts", "checkpoints", "vision", "yolov8n_rail_run", "weights", "best.pt"),
            os.path.join("artifacts", "checkpoints", "yolov8n_rail_best.pt"),
            "yolov8n.pt",
        ]
        for c in candidates:
            if os.path.exists(c):
                model_path = c
                break

    if args.format in ["onnx", "all"]:
        onnx_file = export_yolo_to_onnx(model_path, output_dir=args.outdir, img_size=args.imgsz, force=args.force)
        if args.format == "all" or args.format == "int8":
            quantize_onnx_int8(onnx_file, force=args.force)
    elif args.format == "int8":
        base_onnx = str(Path(args.outdir) / (Path(model_path).stem + ".onnx"))
        if not os.path.exists(base_onnx):
            base_onnx = export_yolo_to_onnx(model_path, output_dir=args.outdir, img_size=args.imgsz, force=args.force)
        quantize_onnx_int8(base_onnx, force=args.force)
