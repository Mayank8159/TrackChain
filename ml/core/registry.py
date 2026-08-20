# Central Model Registry & Asset Librarian for TrackChain (tc.v1 SOTA).

import os
from pathlib import Path
from typing import Any, Dict, Optional

_MODEL_REGISTRY: Dict[str, Any] = {}


def get_repo_root() -> Path:
    """Return the absolute path to the TrackChain repository root."""
    return Path(__file__).resolve().parent.parent.parent


class ModelRegistry:
    """
    Central librarian for model architectures, base weights, trained checkpoints,
    and quantized edge deployment exports.
    """
    ROOT: Path = get_repo_root()
    ARTIFACTS_DIR: Path = ROOT / "artifacts"
    BASE_DIR: Path = ARTIFACTS_DIR / "base"
    CHECKPOINTS_DIR: Path = ARTIFACTS_DIR / "checkpoints"
    EXPORTS_DIR: Path = ARTIFACTS_DIR / "exports"
    CALIBRATION_DIR: Path = ARTIFACTS_DIR / "calibration"

    @classmethod
    def get_base_weights(cls, domain: str, model_name: str) -> Path:
        """Return path to frozen/pretrained base weights (e.g. artifacts/base/vision/yolov8n.pt)."""
        target = cls.BASE_DIR / domain / model_name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    @classmethod
    def get_trained_weights(cls, domain: str, model_name: str, version: Optional[str] = None) -> Path:
        """Return path to trained checkpoint (e.g. artifacts/checkpoints/vision/yolo_rail_v0.1.pt)."""
        suffix = f"_{version}" if version else ""
        stem, ext = os.path.splitext(model_name)
        fname = f"{stem}{suffix}{ext}" if ext else f"{model_name}{suffix}.pt"
        target = cls.CHECKPOINTS_DIR / domain / fname
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    @classmethod
    def get_export_path(cls, domain: str, model_name: str, fmt: str = "onnx") -> Path:
        """Return path to edge deployment artifact (e.g. artifacts/exports/vision/yolo_rail_v0.1_int8.onnx)."""
        stem, _ = os.path.splitext(model_name)
        fname = f"{stem}.{fmt}"
        target = cls.EXPORTS_DIR / domain / fname
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    @classmethod
    def get_calibration_path(cls, model_name: str) -> Path:
        """Return path to calibration metadata (e.g. artifacts/calibration/yolo_temp_scale.json)."""
        stem, _ = os.path.splitext(model_name)
        target = cls.CALIBRATION_DIR / f"{stem}_calibration.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target


def register_model(name: str):
    """Decorator to register a model class or factory function."""
    def decorator(cls_or_fn):
        _MODEL_REGISTRY[name] = cls_or_fn
        return cls_or_fn
    return decorator


def load_model(
    model_name: str,
    checkpoint_path: Optional[str] = None,
    **kwargs,
) -> Any:
    """Instantiate and load weights for any model registered by name."""
    if model_name not in _MODEL_REGISTRY:
        raise ValueError(
            f"Model '{model_name}' not found in registry. Available: {list(_MODEL_REGISTRY.keys())}"
        )

    model_cls = _MODEL_REGISTRY[model_name]
    instance = model_cls(**kwargs)

    if checkpoint_path and os.path.exists(checkpoint_path):
        if hasattr(instance, "load_weights"):
            instance.load_weights(checkpoint_path)

    return instance
