"""
Train PatchCore visual anomaly detector script (tc.v1 SOTA).
Accelerated multi-scale feature extraction, fast minimax coreset selection,
and explicit True Positive Rate (TPR) / False Positive Rate (FPR) benchmark verification.
"""

import sys
import argparse
from pathlib import Path

# Add repo root to python path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.training.train_anomaly import train_patchcore

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train PatchCore visual anomaly detector.")
    parser.add_argument("--data", "--data-path", dest="data", default="data/external/rail_normal_expanded", help="Path to normal dataset directory")
    parser.add_argument("--config", default="ml/configs/anomaly.yaml", help="Path to anomaly.yaml")
    parser.add_argument("--coreset_ratio", "--ratio", dest="coreset_ratio", type=float, default=0.10, help="Coreset subsampling ratio")
    parser.add_argument("--max_coreset", type=int, default=3000, help="Maximum number of coreset patches to retain")
    parser.add_argument("--batch_size", "--batch", type=int, default=32, help="Batch size for feature extraction")
    parser.add_argument("--fpr_target", type=float, default=0.01, help="Target FPR on normal validation track (e.g. 0.01 for P99)")
    parser.add_argument("--device", default="auto", help="Device ('auto', 'cuda', or 'cpu')")
    parser.add_argument("--out-ckpt", default=None, help="Output memory bank path")
    parser.add_argument("--out-calib", default=None, help="Output calibration JSON path")
    args = parser.parse_args()

    train_patchcore(
        data_dir=args.data,
        config_path=args.config,
        sampling_ratio=args.coreset_ratio,
        max_coreset_size=args.max_coreset,
        batch_size=args.batch_size,
        device=args.device,
        output_checkpoint=args.out_ckpt,
        output_calibration=args.out_calib,
    )
