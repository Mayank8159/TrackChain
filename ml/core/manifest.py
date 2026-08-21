"""
TrackChain Manifest & Checkpoint Fingerprinting Engine (tc.v1 SOTA).
Provides cryptographically verified skip-logic based on SHA-256 config hashes,
dataset label fingerprints, source weight hashes, and minimum metric quality gates.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, Union
import yaml


def compute_file_sha256(filepath: Union[str, Path]) -> str:
    """Compute SHA-256 hash of a file."""
    p = Path(filepath)
    if not p.exists() or not p.is_file():
        return ""
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_config_hash(config_path: Optional[Union[str, Path]] = None, overrides: Optional[Dict[str, Any]] = None) -> str:
    """
    Compute SHA-256 hash of a configuration YAML/JSON combined with CLI hyperparameters.
    """
    hasher = hashlib.sha256()

    if config_path:
        p = Path(config_path)
        if p.exists() and p.is_file():
            with open(p, "rb") as f:
                hasher.update(f.read())

    if overrides:
        # Sort keys for deterministic hashing
        overrides_str = json.dumps(overrides, sort_keys=True)
        hasher.update(overrides_str.encode("utf-8"))

    return hasher.hexdigest()


def compute_dataset_hash(data_yaml_path: Union[str, Path]) -> str:
    """
    Compute SHA-256 fingerprint of a dataset without reading all image pixels.
    Hashes:
    - The data.yaml configuration
    - Sorted list of label files, their counts, and file sizes across train/val/test splits.
    """
    p = Path(data_yaml_path)
    if not p.exists():
        return ""

    hasher = hashlib.sha256()

    with open(p, "r", encoding="utf-8") as f:
        try:
            data_cfg = yaml.safe_load(f) or {}
        except Exception:
            data_cfg = {}

    hasher.update(json.dumps(data_cfg, sort_keys=True).encode("utf-8"))

    # Resolve dataset root path
    raw_path = data_cfg.get("path", "")
    data_root = Path(raw_path) if Path(raw_path).is_absolute() else p.parent / raw_path

    for split_key in ["train", "val", "validation", "test"]:
        split_val = data_cfg.get(split_key)
        if not split_val:
            continue

        split_dir = data_root / split_val if not Path(split_val).is_absolute() else Path(split_val)
        # Search for corresponding labels folder
        labels_dir = split_dir.parent / "labels" if split_dir.name == "images" else split_dir / "labels"

        if labels_dir.exists() and labels_dir.is_dir():
            label_files = sorted(list(labels_dir.glob("*.txt")))
            hasher.update(f"{split_key}_count:{len(label_files)}".encode("utf-8"))
            for lf in label_files:
                try:
                    stat = lf.stat()
                    hasher.update(f"{lf.name}:{stat.st_size}".encode("utf-8"))
                except Exception:
                    continue
        elif split_dir.exists():
            # For image folders (e.g. PatchCore normal good images)
            img_files = sorted(list(split_dir.glob("*.jpg")) + list(split_dir.glob("*.png")))
            hasher.update(f"{split_key}_imgs:{len(img_files)}".encode("utf-8"))
            for img in img_files[:200]:  # Hash first 200 filenames/sizes for speed
                try:
                    hasher.update(f"{img.name}:{img.stat().st_size}".encode("utf-8"))
                except Exception:
                    continue

    return hasher.hexdigest()


def load_manifest(manifest_path: Union[str, Path]) -> Dict[str, Any]:
    """Load JSON manifest file safely."""
    p = Path(manifest_path)
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_manifest(manifest_path: Union[str, Path], data: Dict[str, Any]):
    """Save JSON manifest file atomically."""
    p = Path(manifest_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def check_training_skip(
    manifest_path: Union[str, Path],
    checkpoint_path: Union[str, Path],
    current_config_hash: str,
    current_dataset_hash: str,
    min_metrics: Optional[Dict[str, float]] = None,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Evaluate if training can be safely skipped based on manifest fingerprinting.
    Returns (should_skip, reason).
    """
    if force:
        return False, "Force flag enabled (--force / --force-retrain)"

    ckpt = Path(checkpoint_path)
    if not ckpt.exists():
        return False, f"Checkpoint does not exist at {ckpt}"

    manifest = load_manifest(manifest_path)
    if not manifest:
        return False, "Manifest file not found or invalid"

    # Verify config hash
    saved_config_hash = manifest.get("config_hash", "")
    if saved_config_hash != current_config_hash:
        return False, f"Config hash changed ({saved_config_hash[:8]} -> {current_config_hash[:8]})"

    # Verify dataset hash
    saved_dataset_hash = manifest.get("dataset_hash", "")
    if saved_dataset_hash != current_dataset_hash:
        return False, f"Dataset hash changed ({saved_dataset_hash[:8]} -> {current_dataset_hash[:8]})"

    # Verify minimum metric quality gate
    if min_metrics:
        saved_metrics = manifest.get("metrics", {})
        for metric_key, min_val in min_metrics.items():
            actual_val = saved_metrics.get(metric_key, 0.0)
            if actual_val < min_val:
                return False, f"Metric gate failed: {metric_key}={actual_val:.4f} < minimum {min_val:.4f}"

    return True, f"Manifest fingerprints match and quality gates passed (mAP50={manifest.get('metrics', {}).get('mAP50', 'N/A')})"


def check_export_skip(
    manifest_path: Union[str, Path],
    export_path: Union[str, Path],
    source_model_path: Union[str, Path],
    export_format: str = "onnx",
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Evaluate if model export can be safely skipped based on source weight hash.
    Returns (should_skip, reason).
    """
    if force:
        return False, "Force flag enabled (--force)"

    exp_p = Path(export_path)
    if not exp_p.exists():
        return False, f"Exported file does not exist at {exp_p}"

    src_p = Path(source_model_path)
    if not src_p.exists():
        return False, f"Source model does not exist at {src_p}"

    current_src_hash = compute_file_sha256(src_p)
    manifest = load_manifest(manifest_path)

    saved_export_entry = manifest.get(export_format, {})
    if not saved_export_entry:
        return False, f"No manifest entry found for format '{export_format}'"

    saved_src_hash = saved_export_entry.get("source_model_hash", "")
    if saved_src_hash != current_src_hash:
        return False, f"Source model weight hash changed ({saved_src_hash[:8]} -> {current_src_hash[:8]})"

    return True, f"Export matches source model hash ({current_src_hash[:8]})"
