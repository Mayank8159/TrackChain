"""
TrackChain CLI Step Skip-Logic Evaluator (tc.v1 SOTA).
Used by ml/scripts/run.sh to evaluate manifest fingerprints and quality gates.

Usage:
  python ml/scripts/should_skip.py --step train_yolo [--force]
  Exit code 0: Skip the step (valid checkpoint & manifest found)
  Exit code 1: Run the step (missing, modified config/dataset, or failed gate)
"""

import sys
import argparse
from pathlib import Path

# Add repo root to python path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.core.manifest import (
    compute_file_sha256,
    compute_config_hash,
    compute_dataset_hash,
    check_training_skip,
    check_export_skip,
    load_manifest,
)


def evaluate_step(step_name: str, force: bool = False) -> bool:
    """Returns True if step should be SKIPPED, False if step should RUN."""
    if force:
        print(f"[{step_name}] Force flag enabled. Running step.")
        return False

    if step_name == "train_yolo":
        # Resolve dataset yaml
        data_yaml = repo_root / "data" / "external" / "rail_defects_expanded" / "data.yaml"
        if not data_yaml.exists():
            data_yaml = repo_root / "data" / "external" / "rail_defects" / "data.yaml"

        config_yaml = repo_root / "ml" / "configs" / "detector.yaml"
        ckpt = repo_root / "artifacts" / "checkpoints" / "vision" / "yolov8n_rail_best.pt"
        manifest_p = repo_root / "artifacts" / "checkpoints" / "vision" / "yolo_manifest.json"

        cfg_hash = compute_config_hash(config_yaml, overrides={"imgsz": 960, "freeze": 10, "dropout": 0.1, "close_mosaic": 10})
        data_hash = compute_dataset_hash(data_yaml)

        skip, reason = check_training_skip(
            manifest_path=manifest_p,
            checkpoint_path=ckpt,
            current_config_hash=cfg_hash,
            current_dataset_hash=data_hash,
            min_metrics={"mAP50": 0.25},
            force=force,
        )
        if skip:
            print(f"[{step_name}] SKIP: {reason}")
            return True
        else:
            print(f"[{step_name}] RUN: {reason}")
            return False

    elif step_name == "export_yolo_onnx":
        src_pt = repo_root / "artifacts" / "checkpoints" / "vision" / "yolov8n_rail_best.pt"
        export_file = repo_root / "artifacts" / "exports" / "yolov8n_rail_best.onnx"
        manifest_p = repo_root / "artifacts" / "exports" / "export_manifest.json"

        skip, reason = check_export_skip(
            manifest_path=manifest_p,
            export_path=export_file,
            source_model_path=src_pt,
            export_format="onnx",
            force=force,
        )
        if skip:
            print(f"[{step_name}] SKIP: {reason}")
            return True
        else:
            print(f"[{step_name}] RUN: {reason}")
            return False

    elif step_name == "export_yolo_int8":
        src_pt = repo_root / "artifacts" / "checkpoints" / "vision" / "yolov8n_rail_best.pt"
        export_file = repo_root / "artifacts" / "exports" / "yolov8n_rail_best_int8.onnx"
        manifest_p = repo_root / "artifacts" / "exports" / "export_manifest.json"

        skip, reason = check_export_skip(
            manifest_path=manifest_p,
            export_path=export_file,
            source_model_path=src_pt,
            export_format="int8",
            force=force,
        )
        if skip:
            print(f"[{step_name}] SKIP: {reason}")
            return True
        else:
            print(f"[{step_name}] RUN: {reason}")
            return False

    elif step_name == "train_patchcore":
        ckpt = repo_root / "artifacts" / "checkpoints" / "vision" / "patchcore_memory_bank.npz"
        calib = repo_root / "artifacts" / "calibration" / "patchcore_calibration.json"
        if ckpt.exists() and calib.exists():
            print(f"[{step_name}] SKIP: PatchCore memory bank and calibration exist.")
            return True
        print(f"[{step_name}] RUN: Memory bank or calibration missing.")
        return False

    elif step_name == "train_bilstm":
        ckpt = repo_root / "artifacts" / "checkpoints" / "geometry" / "bilstm_fault_typing_enhanced.pt"
        calib = repo_root / "artifacts" / "calibration" / "bilstm_temp.json"
        if ckpt.exists() and calib.exists():
            print(f"[{step_name}] SKIP: Bi-LSTM checkpoint and calibration exist.")
            return True
        print(f"[{step_name}] RUN: Bi-LSTM weights or calibration missing.")
        return False

    elif step_name == "train_vae":
        ckpt = repo_root / "artifacts" / "checkpoints" / "geometry" / "sequence_vae_enhanced.pt"
        calib = repo_root / "artifacts" / "calibration" / "vae_calibration.json"
        if ckpt.exists() and calib.exists():
            print(f"[{step_name}] SKIP: Seq-VAE checkpoint and EVT calibration exist.")
            return True
        print(f"[{step_name}] RUN: Seq-VAE weights or calibration missing.")
        return False

    # Default: Run step
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate step skip-logic using manifests.")
    parser.add_argument("--step", required=True, help="Step name to evaluate")
    parser.add_argument("--force", action="store_true", help="Force execution")
    args = parser.parse_args()

    should_skip = evaluate_step(step_name=args.step, force=args.force)
    # Exit 0 if skipping, Exit 1 if running
    sys.exit(0 if should_skip else 1)
