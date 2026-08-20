# Load any model by name from artifacts/checkpoints.

import os
from typing import Any, Dict, Optional

_MODEL_REGISTRY: Dict[str, Any] = {}


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
