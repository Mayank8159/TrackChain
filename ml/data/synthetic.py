"""
Generate synthetic vision and geometry data with known fault signatures (tc.v1 SOTA).
Provides multi-modal generation for:
  - Continuous track geometry conforming to EN 13848-1
  - Procedural vision defect injection (crack, missing fastener, defective clip, obstruction)
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import cv2

from ml.data.synthetic_vision import (
    SyntheticRailDefectGenerator,
    sanitize_bbox,
    CLASS_MAPPING,
    CLASS_NAMES,
)


def generate_synthetic_geometry(
    length_m: float = 1000.0,
    step_m: float = 0.25,
    fault_probability: float = 0.05,
    random_seed: int = 42,
) -> Dict[str, np.ndarray]:
    """Generate synthetic continuous track geometry conforming to EN 13848-1."""
    np.random.seed(random_seed)
    n_points = int(length_m / step_m)
    chainage = np.linspace(0, length_m, n_points)

    # Base nominal signals
    gauge = 1435.0 + np.random.normal(0, 0.8, n_points)
    cant = 10.0 * np.sin(chainage / 200.0) + np.random.normal(0, 1.2, n_points)
    twist = np.gradient(cant, step_m) * 3.0 + np.random.normal(0, 0.2, n_points)
    unevenness = 0.5 * np.sin(chainage / 15.0) + np.random.normal(0, 0.3, n_points)
    alignment = 0.6 * np.cos(chainage / 25.0) + np.random.normal(0, 0.3, n_points)
    vibration_rms = 0.8 + 0.2 * np.abs(np.random.normal(0, 1.0, n_points))

    # Inject discrete fault signatures
    labels = np.zeros(n_points, dtype=int)
    n_faults = int(length_m * fault_probability / 50.0)

    for _ in range(n_faults):
        center_idx = np.random.randint(50, n_points - 50)
        fault_type = np.random.choice([1, 2, 3])  # 1: Gauge widening, 2: Twist, 3: Corrugation
        window_size = np.random.randint(10, 40)
        idx_range = slice(center_idx - window_size // 2, center_idx + window_size // 2)

        if fault_type == 1:
            gauge[idx_range] += np.random.uniform(8.0, 18.0)
            labels[idx_range] = 1
        elif fault_type == 2:
            twist[idx_range] += np.random.uniform(3.5, 6.0) * np.sign(np.random.randn())
            labels[idx_range] = 2
        elif fault_type == 3:
            unevenness[idx_range] += 3.0 * np.sin(np.arange(window_size) * 0.8)
            vibration_rms[idx_range] += np.random.uniform(1.8, 3.5)
            labels[idx_range] = 3

    return {
        "chainage_m": chainage,
        "gauge_mm": gauge,
        "cant_mm": cant,
        "twist_mm_per_m": twist,
        "vertical_unevenness_mm": unevenness,
        "alignment_mm": alignment,
        "vibration_rms_g": vibration_rms,
        "fault_labels": labels,
    }


def generate_synthetic_defect_image(
    defect_type: str = "crack",
    height: int = 640,
    width: int = 640,
) -> Tuple[np.ndarray, Optional[List[float]]]:
    """
    Generate high-fidelity synthetic rail surface patch with specific defect and YOLO bounding box.
    """
    # Create base track texture
    base = np.zeros((height, width, 3), dtype=np.uint8)
    ballast = np.array([80, 75, 65], dtype=np.float32)
    noise = np.random.normal(0, 15, (height, width, 3))
    base[:] = np.clip(ballast + noise, 0, 255).astype(np.uint8)

    # Add rails
    rail_w = int(width * 0.08)
    for offset in [int(width * 0.32), int(width * 0.68)]:
        cv2.rectangle(base, (offset - rail_w // 2, 0), (offset + rail_w // 2, height), (55, 55, 60), -1)
        cv2.line(base, (offset, 0), (offset, height), (140, 140, 150), 3)

    gen = SyntheticRailDefectGenerator()
    if defect_type == "crack":
        return gen.inject_crack(base)
    elif defect_type in ["missing_fastener", "fastener"]:
        return gen.inject_missing_fastener(base)
    elif defect_type in ["defective_clip", "damaged_fastener", "clip"]:
        return gen.inject_defective_clip(base)
    elif defect_type in ["obstruction", "debris"]:
        return gen.inject_obstruction(base)
    else:
        return gen.inject_crack(base)


__all__ = [
    "generate_synthetic_geometry",
    "generate_synthetic_defect_image",
    "SyntheticRailDefectGenerator",
    "sanitize_bbox",
    "CLASS_MAPPING",
    "CLASS_NAMES",
]
