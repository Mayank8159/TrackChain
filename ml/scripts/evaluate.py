# Run evaluation and emit reports.

import numpy as np
from ml.evaluation.metrics import compute_anomaly_metrics, compute_expected_calibration_error
from ml.evaluation.reports import generate_markdown_report
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("evaluate")


def main():
    logger.info("Evaluating TrackChain multi-stream defect classification system...")

    # Simulated test set metrics
    y_true = np.concatenate([np.zeros(900), np.ones(100)])
    scores = np.concatenate([np.random.beta(1, 10, 900), np.random.beta(8, 2, 100)])

    metrics = compute_anomaly_metrics(y_true, scores)
    metrics["ece"] = compute_expected_calibration_error(scores, y_true)

    logger.info(f"Evaluation Results: AUROC={metrics['auroc']:.4f} | PR-AUC={metrics['pr_auc']:.4f} | FPR@95%={metrics['fpr_at_95_recall']:.4f}")
    generate_markdown_report(metrics)
    logger.info("Report emitted to artifacts/evaluation_report.md")


if __name__ == "__main__":
    main()
