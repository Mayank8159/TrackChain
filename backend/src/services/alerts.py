# Alert dispatch (email/SMS) when a defect crosses a severity threshold.

import logging
from src.schemas.defects import DefectCreate

logger = logging.getLogger("trackchain.alerts")


def dispatch_defect_alert(defect: DefectCreate):
    """Dispatch instant notifications for high and critical railway defects."""
    if defect.severity in ["high", "critical"]:
        logger.warning(
            f"🚨 CRITICAL RAILWAY DEFECT ALERT: [{defect.defect_class.upper()}] "
            f"detected at Chainage {(defect.chainage_m / 1000):.3f} km. "
            f"Confidence: {defect.confidence:.2%}. Session: {defect.session_id}"
        )
        # Integration hooks for SMS / PagerDuty / Railway Control Center webhook
        return True
    return False
