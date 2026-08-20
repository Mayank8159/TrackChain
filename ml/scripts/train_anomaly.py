# Train PatchCore visual anomaly detector script (tc.v1 SOTA).

import sys
from pathlib import Path

# Add repo root to python path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

from ml.training.train_anomaly import train_patchcore

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train PatchCore visual anomaly detector.")
    parser.add_argument("--data", default="data/external/rail_normal_only", help="Path to normal dataset directory")
    parser.add_argument("--config", default="ml/configs/anomaly.yaml", help="Path to anomaly.yaml")
    parser.add_argument("--coreset_ratio", "--ratio", dest="coreset_ratio", type=float, default=0.10, help="Coreset subsampling ratio")
    parser.add_argument("--fpr_target", type=float, default=0.01, help="Target FPR on normal validation track (e.g. 0.01 for P99)")
    parser.add_argument("--device", default="cpu", help="Device ('cpu' or 'cuda')")
    args = parser.parse_args()

    train_patchcore(
        data_dir=args.data,
        config_path=args.config,
        sampling_ratio=args.coreset_ratio,
        device=args.device,
    )
