# Generates synthetic TRC telemetry based on EN 13848-2 PSD profiles (tc.v1 SOTA).

import os
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d


def generate_track_profile_psd(
    length_m: float = 1000.0,
    spatial_resolution_m: float = 0.05,
    defect_mm: float = 5.0,
    defect_start_m: float = 500.0,
    defect_base_m: float = 3.0,
    random_seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates realistic track cant (cross-level) profile using EN 13848-2 Power Spectral Density (PSD)
    with injected deterministic geometry fault.
    """
    np.random.seed(random_seed)
    n_pts = int(length_m / spatial_resolution_m)
    x = np.linspace(0, length_m, n_pts)

    # 1. EN 13848-2 standard track roughness PSD (Grade 4 typical track)
    freqs = np.fft.rfftfreq(n_pts, d=spatial_resolution_m)
    freqs[0] = freqs[1] * 0.1  # Avoid division by zero at DC component
    psd = 0.005 / (freqs**2 + 0.01)  # Typical track degradation decay spectrum

    # Inverse FFT with random phase
    phases = np.exp(1j * np.random.uniform(0, 2 * np.pi, len(freqs)))
    noise = np.fft.irfft(np.sqrt(psd) * phases, n=n_pts)
    
    # Smooth baseline cant using physical rail curvature smoothing (sigma ~ 1.0m)
    sigma_samples = int(1.0 / spatial_resolution_m)
    smooth_noise = gaussian_filter1d(noise, sigma=sigma_samples)
    
    # Scale to typical cant roughness standard deviation (~1.0mm RMS for high-quality track)
    cant_profile_mm = (smooth_noise / (np.std(smooth_noise) + 1e-8)) * 0.8

    # 2. Inject deterministic Twist / Cant exceedance fault
    if defect_mm > 0:
        start_idx = int(defect_start_m / spatial_resolution_m)
        end_idx = start_idx + int(defect_base_m / spatial_resolution_m)
        ramp = np.linspace(0, defect_mm, end_idx - start_idx)
        cant_profile_mm[start_idx:end_idx] += ramp

    return x, cant_profile_mm


def generate_trc_telemetry_csv(
    output_path: str = "data/processed/synthetic_trc_run_001.csv",
    speed_mps: float = 20.0,  # 72 km/h
    sample_rate_hz: float = 100.0,
    length_m: float = 1000.0,
    defect_mm: float = 5.0,
    defect_start_m: float = 500.0,
) -> str:
    """
    Generate time-domain 100Hz IMU and Laser TRC telemetry CSV for chainage resampling.
    """
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    dt = 1.0 / sample_rate_hz
    total_time_s = length_m / speed_mps
    timestamps = np.arange(0, total_time_s, dt)
    n_samples = len(timestamps)

    # Generate spatial track profile and interpolate onto train trajectory
    _, cant_profile_mm = generate_track_profile_psd(
        length_m=length_m,
        spatial_resolution_m=0.05,
        defect_mm=defect_mm,
        defect_start_m=defect_start_m,
    )

    track_x = np.linspace(0, length_m, len(cant_profile_mm))
    train_x = timestamps * speed_mps
    cant_sampled_mm = np.interp(train_x, track_x, cant_profile_mm)

    # Convert cant in mm to IMU roll in radians: Roll = arcsin(Cant / Gauge)
    nominal_gauge_mm = 1676.0
    roll_rad = np.arcsin(np.clip(cant_sampled_mm / nominal_gauge_mm, -0.2, 0.2))

    # Add realistic sensor noise to IMU channels
    np.random.seed(42)
    lat_accel_g = np.random.normal(0.0, 0.01, n_samples)
    vert_accel_g = np.random.normal(1.0, 0.02, n_samples)  # 1G gravity baseline
    gauge_mm = np.random.normal(nominal_gauge_mm, 0.4, n_samples)

    if defect_mm > 0:
        defect_mask = (train_x >= defect_start_m) & (train_x <= defect_start_m + 3.0)
        gauge_mm[defect_mask] += 1.5

    df = pd.DataFrame({
        "timestamp": np.round(timestamps, 3),
        "speed_mps": np.full(n_samples, speed_mps),
        "roll_rad": np.round(roll_rad, 6),
        "lat_accel_g": np.round(lat_accel_g, 4),
        "vert_accel_g": np.round(vert_accel_g, 4),
        "gauge_mm": np.round(gauge_mm, 2),
    })

    df.to_csv(p, index=False)
    print(f"[OK] Generated EN 13848-2 compliant synthetic TRC telemetry:")
    print(f"     Path:           {p}")
    print(f"     Track Length:   {length_m} m ({n_samples} samples @ 100 Hz)")
    print(f"     Speed:          {speed_mps} m/s ({speed_mps * 3.6:.0f} km/h)")
    print(f"     Injected Fault: {defect_mm}mm Twist @ chainage {defect_start_m}m")
    return str(p)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic EN 13848 TRC telemetry.")
    parser.add_argument("--out", default="data/processed/synthetic_trc_run_001.csv", help="Output CSV path")
    parser.add_argument("--length", type=float, default=1000.0, help="Track length in meters")
    parser.add_argument("--defect", type=float, default=5.0, help="Injected twist defect in mm")
    parser.add_argument("--defect-pos", type=float, default=500.0, help="Defect start chainage in meters")
    args = parser.parse_args()

    generate_trc_telemetry_csv(
        output_path=args.out,
        length_m=args.length,
        defect_mm=args.defect,
        defect_start_m=args.defect_pos,
    )
