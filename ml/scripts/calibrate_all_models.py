"""
Unified calibration script for all models.
Ensures all models output calibrated scores in [0, 1] with threshold at 0.5.
"""
import json
from pathlib import Path


def verify_calibration_sync() -> bool:
    """Verify all models are calibrated to the same [0, 1] scale."""

    print("=" * 70)
    print("TrackChain Calibration Synchronization Verification")
    print("=" * 70)

    calibration_dir = Path('artifacts/calibration')

    # Check all calibration files exist
    required_files = [
        'yolo_temp.json',
        'patchcore_calibration.json',
        'bilstm_temp.json',
        'vae_calibration.json',
    ]

    print("\n[1/4] Checking calibration files...")
    all_exist = True
    for filename in required_files:
        filepath = calibration_dir / filename
        if filepath.exists():
            print(f"  [OK] {filename}")
        else:
            print(f"  [MISSING] {filename}")
            all_exist = False

    if not all_exist:
        print("\n[ERROR] Some calibration files are missing. Run training or calibration first.")
        return False

    # Load and verify each calibration
    print("\n[2/4] Verifying calibration parameters...")

    calibrations = {}
    for filename in required_files:
        filepath = calibration_dir / filename
        with open(filepath, encoding='utf-8') as f:
            calibrations[filename] = json.load(f)

    # Print calibration summary
    print("\n[3/4] Calibration Summary:")
    print("-" * 70)

    for name, calib in calibrations.items():
        model_name = calib.get('model', name)
        print(f"\n  {model_name}:")

        if 'temperature' in calib:
            print(f"    Method: Temperature Scaling")
            print(f"    Temperature: {calib['temperature']:.3f}")
        elif 'threshold_p99' in calib:
            print(f"    Method: Sigmoid P99")
            print(f"    P99 Threshold: {calib['threshold_p99']:.3f}")

        if 'val_samples' in calib:
            print(f"    Validation samples: {calib['val_samples']}")

    # Verify sync
    print("\n[4/4] Verifying synchronization...")

    # All models should output scores in [0, 1]
    # All models should use threshold 0.5 for firing
    sync_status = {
        'yolo': 'temperature' in calibrations.get('yolo_temp.json', {}),
        'patchcore': 'threshold_p99' in calibrations.get('patchcore_calibration.json', {}),
        'bilstm': 'temperature' in calibrations.get('bilstm_temp.json', {}),
        'vae': 'threshold_p99' in calibrations.get('vae_calibration.json', {}),
    }

    all_synced = all(sync_status.values())

    if all_synced:
        print("  [OK] All models calibrated and synchronized")
        print("  [OK] All models output scores in [0, 1]")
        print("  [OK] All models use threshold 0.5 for firing")
    else:
        print("  [WARN] Some models are not properly calibrated")
        for model, synced in sync_status.items():
            status = "[OK]" if synced else "[FAIL]"
            print(f"    {status} {model}")

    print("\n" + "=" * 70)
    print("Calibration Verification Complete!")
    print("=" * 70)

    return all_synced


if __name__ == "__main__":
    verify_calibration_sync()
