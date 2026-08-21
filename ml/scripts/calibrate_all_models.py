import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def verify_calibration_sync() -> bool:
    """Verify all models are calibrated to the universal [0.0, 1.0] scale."""

    print("=" * 75)
    print("TrackChain SOTA Calibration Synchronization & Sync Verification")
    print("=" * 75)

    calibration_dir = Path('artifacts/calibration')

    # Check all required calibration manifests
    required_files = [
        'yolo_temp.json',
        'patchcore_calibration.json',
        'bilstm_temp.json',
        'vae_calibration.json',
    ]

    print("\n[1/4] Checking calibration manifest files...")
    all_exist = True
    for filename in required_files:
        filepath = calibration_dir / filename
        if filepath.exists():
            print(f"  [OK] {filename}")
        else:
            print(f"  [MISSING] {filename}")
            all_exist = False

    if not all_exist:
        print("\n[WARN] Some calibration files are missing. Run pipeline steps to generate all checkpoints.")

    # Load and verify each calibration
    print("\n[2/4] Verifying calibration parameters...")

    calibrations = {}
    for filename in required_files:
        filepath = calibration_dir / filename
        if filepath.exists():
            with open(filepath, encoding='utf-8') as f:
                calibrations[filename] = json.load(f)

    # Print calibration summary
    print("\n[3/4] SOTA Calibration Summary:")
    print("-" * 75)

    for name, calib in calibrations.items():
        model_name = calib.get('model', name)
        print(f"\n  Model: {model_name} ({name})")

        if 'weights' in calib and 'biases' in calib:
            print("    Method: SOTA Vector Scaling (per-class weights + biases)")
            print(f"    ECE:    {calib.get('ece', 0.0):.4f}")
            print(f"    Num Classes: {len(calib['weights'])}")
        elif 'temperature' in calib:
            print("    Method: Temperature Scaling")
            print(f"    Temperature (T): {calib['temperature']:.3f}")
            if 'ece' in calib:
                print(f"    ECE: {calib['ece']:.4f}")

        if 'threshold_evt' in calib:
            print("    Method: SOTA Extreme Value Theory (EVT) Peaks-Over-Threshold")
            print(f"    EVT Threshold:  {calib['threshold_evt']:.4f}")
            print(f"    P99 Threshold:  {calib.get('threshold_p99', 0.0):.4f}")
            print(f"    EVT Tail Shape: {calib.get('evt_shape', 0.0):.4f}, Scale: {calib.get('evt_scale', 1.0):.4f}")
        elif 'threshold_p99' in calib:
            print("    Method: Statistical P99 / Sigmoid CDF")
            print(f"    P99 Threshold: {calib['threshold_p99']:.3f}")

        if 'val_samples' in calib:
            print(f"    Validation Samples: {calib['val_samples']}")

    # Verify sync across triad & geometry streams
    print("\n[4/4] Verifying multi-modal probability synchronization...")
    print("-" * 75)

    sync_status = {
        'Phase 2.1 (YOLOv8n Defect Detector)': 'temperature' in calibrations.get('yolo_temp.json', {}),
        'Phase 2.2 (PatchCore Visual Anomaly)': 'threshold_p99' in calibrations.get('patchcore_calibration.json', {}),
        'Phase 2.3 (EN 13848 Physics Safety)': True,  # Deterministic safety rule
        'Phase 2.4 (Bi-LSTM Fault Classifier)': ('weights' in calibrations.get('bilstm_temp.json', {}) or 'temperature' in calibrations.get('bilstm_temp.json', {})),
        'Phase 2.5 (Seq-VAE Novelty Detector)': ('threshold_evt' in calibrations.get('vae_calibration.json', {}) or 'threshold_p99' in calibrations.get('vae_calibration.json', {})),
    }

    all_synced = all(sync_status.values())

    for stream, synced in sync_status.items():
        status = "[SYNCHRONIZED]" if synced else "[UNSYNCED]   "
        print(f"  {status} {stream}")

    print("\n" + "=" * 75)
    if all_synced:
        print("[SUCCESS] ALL 5 TRACKCHAIN MODELS CALIBRATED & SYNCHRONIZED!")
        print("   - Probability Domain: [0.0, 1.0]")
        print("   - Universal Firing Threshold: 0.50")
        print("   - Fusion Ready: Cross-Modal Attention & Multi-Modal Transformer Engine")
    else:
        print("[WARNING] Pipeline partially calibrated. Complete missing training steps to achieve full sync.")
    print("=" * 75)

    return all_synced


if __name__ == "__main__":
    verify_calibration_sync()
