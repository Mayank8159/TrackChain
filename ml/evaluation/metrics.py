# PR/ROC, FPR, and calibration-curve metrics.

from typing import Dict, Tuple
import numpy as np
from sklearn.metrics import (
    precision_recall_curve,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)


def compute_anomaly_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
) -> Dict[str, float]:
    """Compute AUROC, Average Precision (PR-AUC), and FPR at 95% Recall."""
    auroc = float(roc_auc_score(y_true, scores))
    ap = float(average_precision_score(y_true, scores))

    precisions, recalls, thresholds = precision_recall_curve(y_true, scores)
    # Find operating point with recall >= 0.95
    idx = np.where(recalls >= 0.95)[0]
    thresh_95 = thresholds[idx[-1]] if len(idx) > 0 and idx[-1] < len(thresholds) else 0.5

    y_pred = (scores >= thresh_95).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr_at_95_recall = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    return {
        "auroc": auroc,
        "pr_auc": ap,
        "fpr_at_95_recall": fpr_at_95_recall,
        "threshold_95_recall": float(thresh_95),
    }


def compute_expected_calibration_error(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE)."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        bin_idx = (probs > bin_boundaries[i]) & (probs <= bin_boundaries[i + 1])
        bin_count = np.sum(bin_idx)
        if bin_count > 0:
            bin_acc = np.mean(labels[bin_idx])
            bin_conf = np.mean(probs[bin_idx])
            ece += (bin_count / len(probs)) * np.abs(bin_acc - bin_conf)
    return float(ece)
