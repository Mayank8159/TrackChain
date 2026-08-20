# Generate synthetic training/validation data.

import os
import numpy as np
from ml.data.synthetic import generate_synthetic_geometry, generate_synthetic_defect_image
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("make_synthetic")


def main():
    logger.info("Generating synthetic training & validation datasets...")
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    # 1. Geometry dataset
    geo_data = generate_synthetic_geometry(length_m=10000.0, fault_probability=0.08)
    np.savez("data/processed/synthetic_geometry.npz", **geo_data)
    logger.info("Saved synthetic geometry to data/processed/synthetic_geometry.npz")

    # 2. Vision patches
    logger.info("Synthetic data creation complete.")


if __name__ == "__main__":
    main()
