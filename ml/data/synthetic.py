# Generate synthetic vision and geometry data with known fault signatures.

from typing import Dict, List, Tuple
import numpy as np


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
    height: int = 256,
    width: int = 256,
) -> np.ndarray:
    """Generate synthetic grayscale/RGB rail surface patches with defect textures."""
    img = np.random.normal(120, 15, (height, width, 3)).astype(np.uint8)
    
    # Draw dark rail head gradient
    img[:, :, :] = np.clip(img + 30, 0, 255)

    if defect_type == "crack":
        # Draw zigzag dark line
        pts = []
        x = np.random.randint(40, width - 40)
        for y in range(40, height - 40, 10):
            x += np.random.randint(-6, 7)
            pts.append((x, y))
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            # Simple line rasterization
            img[p1[1]:p2[1]+1, min(p1[0], p2[0]):max(p1[0], p2[0])+2] = 20
    elif defect_type == "spalling":
        # Elliptical cavity
        cy, cx = height // 2, width // 2
        y, x = np.ogrid[:height, :width]
        mask = ((x - cx) / 25) ** 2 + ((y - cy) / 15) ** 2 <= 1
        img[mask] = np.random.normal(40, 10, img[mask].shape)

    return img
