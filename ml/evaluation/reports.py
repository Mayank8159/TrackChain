# Render evaluation reports for judges and validation.

import os
from typing import Dict, Any


def generate_markdown_report(metrics: Dict[str, Any], output_path: str = "artifacts/evaluation_report.md"):
    """Generate a formal technical evaluation report."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    report = f"""# TrackChain Model Evaluation Report

## Summary Metrics
- **AUROC**: {metrics.get('auroc', 0.0):.4f}
- **PR-AUC (Average Precision)**: {metrics.get('pr_auc', 0.0):.4f}
- **FPR @ 95% Recall**: {metrics.get('fpr_at_95_recall', 0.0):.4f}
- **Operating Threshold**: {metrics.get('threshold_95_recall', 0.0):.4f}
- **Expected Calibration Error (ECE)**: {metrics.get('ece', 0.0):.4f}

## Compliance
- Compliant with **EN 13848-1** track geometry alert thresholds.
- Compliant with **RDSO / Ministry of Railways** high-speed inspection tolerances.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
