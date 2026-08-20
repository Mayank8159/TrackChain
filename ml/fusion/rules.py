# Rule-based fusion over calibrated signals with persistence (OK/INSPECT_KNOWN/INSPECT_NOVEL).

from typing import List, Optional
from collections import deque
from ml.core.schema import (
    CalibratedSignal,
    SegmentDecision,
    DecisionType,
    DefectClass,
)


class PersistenceRuleFusion:
    """Combines dual-stream calibrated vision and geometry outputs with temporal/spatial persistence."""

    def __init__(
        self,
        persistence_window: int = 3,
        known_threshold: float = 0.70,
        novel_threshold: float = 0.65,
    ):
        self.persistence_window = persistence_window
        self.known_threshold = known_threshold
        self.novel_threshold = novel_threshold
        self.history = deque(maxlen=persistence_window)

    def fuse(
        self,
        window_id: str,
        start_chainage_m: float,
        end_chainage_m: float,
        signals: List[CalibratedSignal],
    ) -> SegmentDecision:
        """Apply rule cascade to output OK, INSPECT_KNOWN, or INSPECT_NOVEL decisions."""
        has_known_fault = False
        has_novel_anomaly = False
        highest_conf = 0.0
        primary_fault: Optional[DefectClass] = None

        for sig in signals:
            if sig.is_anomaly:
                if sig.predicted_class and sig.predicted_class != DefectClass.UNCLASSIFIED:
                    if sig.calibrated_prob >= self.known_threshold:
                        has_known_fault = True
                        if sig.calibrated_prob > highest_conf:
                            highest_conf = sig.calibrated_prob
                            primary_fault = sig.predicted_class
                else:
                    if sig.calibrated_prob >= self.novel_threshold:
                        has_novel_anomaly = True
                        if sig.calibrated_prob > highest_conf:
                            highest_conf = sig.calibrated_prob
                            primary_fault = DefectClass.UNCLASSIFIED

        # Rule evaluation
        if has_known_fault:
            decision = DecisionType.INSPECT_KNOWN
        elif has_novel_anomaly:
            decision = DecisionType.INSPECT_NOVEL
        else:
            decision = DecisionType.OK
            highest_conf = 0.98

        self.history.append(decision)

        # Persistence check: require at least 1 confirmation in history for critical events
        confirmed_decision = decision
        if decision != DecisionType.OK:
            anomaly_count = sum(1 for d in self.history if d != DecisionType.OK)
            if anomaly_count == 1 and self.persistence_window > 1:
                # Single isolated spike, wait for persistence confirmation
                confirmed_decision = DecisionType.OK

        return SegmentDecision(
            window_id=window_id,
            start_chainage_m=start_chainage_m,
            end_chainage_m=end_chainage_m,
            decision=confirmed_decision,
            confidence=highest_conf,
            primary_fault=primary_fault if confirmed_decision != DecisionType.OK else None,
            signals=signals,
        )
