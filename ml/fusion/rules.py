# Rule-based fusion over calibrated signals with persistence (OK/INSPECT_KNOWN/INSPECT_NOVEL) (tc.v1 SOTA).

from typing import List, Optional
from collections import deque
from ml.core.schema import (
    CalibratedSignal,
    SegmentDecision,
    DecisionType,
    DefectClass,
    SignalType,
    DefectFamily,
    SeverityLevel,
)


class PersistenceRuleFusion:
    """Combines dual-stream calibrated vision and geometry outputs with temporal/spatial persistence."""

    def __init__(
        self,
        persistence_window: int = 3,
        known_threshold: float = 0.60,
        novel_threshold: float = 0.60,
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

        highest_known_conf = 0.0
        primary_known_fault: Optional[DefectClass] = None
        known_family: DefectFamily = DefectFamily.VISUAL_COMPONENT

        highest_novel_conf = 0.0
        primary_novel_fault: Optional[DefectClass] = None
        novel_family: DefectFamily = DefectFamily.NOVEL_ANOMALY

        for sig in signals:
            if not sig.is_anomaly:
                continue

            # Determine whether signal is novel vs known
            is_novel = (
                sig.signal_type in (SignalType.VISUAL_NOVEL, SignalType.GEOMETRY_NOVEL)
                or sig.predicted_class in (
                    DefectClass.VISUAL_ANOMALY,
                    DefectClass.GEOMETRY_ANOMALY,
                    DefectClass.UNCLASSIFIED,
                )
            )

            if is_novel:
                if sig.calibrated_prob >= self.novel_threshold:
                    has_novel_anomaly = True
                    if sig.calibrated_prob > highest_novel_conf:
                        highest_novel_conf = sig.calibrated_prob
                        primary_novel_fault = sig.predicted_class or DefectClass.VISUAL_ANOMALY
                        novel_family = DefectFamily.NOVEL_ANOMALY
            else:
                # Known discrete fault (YOLO fastener/crack or EN 13848 twist/gauge/versine)
                if sig.calibrated_prob >= self.known_threshold:
                    has_known_fault = True
                    if sig.calibrated_prob > highest_known_conf:
                        highest_known_conf = sig.calibrated_prob
                        primary_known_fault = sig.predicted_class
                        if sig.signal_type == SignalType.GEOMETRY_KNOWN:
                            known_family = DefectFamily.GEOMETRY
                        else:
                            known_family = DefectFamily.VISUAL_COMPONENT

        # Decision Hierarchy: Known defects take precedence over Novel anomalies
        if has_known_fault:
            decision = DecisionType.INSPECT_KNOWN
            confidence = highest_known_conf
            primary_fault = primary_known_fault
            defect_family = known_family
            if confidence >= 0.80:
                severity = SeverityLevel.CRITICAL
            elif confidence >= 0.65:
                severity = SeverityLevel.HIGH
            else:
                severity = SeverityLevel.MEDIUM
        elif has_novel_anomaly:
            decision = DecisionType.INSPECT_NOVEL
            confidence = highest_novel_conf
            primary_fault = primary_novel_fault or DefectClass.VISUAL_ANOMALY
            defect_family = novel_family
            severity = SeverityLevel.MEDIUM if confidence < 0.85 else SeverityLevel.HIGH
        else:
            decision = DecisionType.OK
            confidence = 0.98
            primary_fault = None
            defect_family = DefectFamily.VISUAL_COMPONENT
            severity = SeverityLevel.NORMAL

        self.history.append(decision)

        # Persistence check: require at least 1 confirmation in history for critical events
        confirmed_decision = decision
        if decision != DecisionType.OK and self.persistence_window > 1:
            anomaly_count = sum(1 for d in self.history if d != DecisionType.OK)
            if anomaly_count == 1:
                # Single isolated spike, hold for spatial persistence confirmation
                confirmed_decision = DecisionType.OK

        return SegmentDecision(
            window_id=window_id,
            start_chainage_m=start_chainage_m,
            end_chainage_m=end_chainage_m,
            decision=confirmed_decision,
            confidence=confidence,
            primary_fault=primary_fault if confirmed_decision != DecisionType.OK else None,
            defect_family=defect_family if confirmed_decision != DecisionType.OK else DefectFamily.VISUAL_COMPONENT,
            severity=severity,
            signals=signals,
        )
