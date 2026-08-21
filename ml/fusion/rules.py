"""
ml/fusion/rules.py
Production Multi-Modal Rule-Based Fusion Engine with:
  1. Confidence-Weighted Voting Matrix
  2. Cross-Modal Correlation Boost (Corroborating Vision + Geometry)
  3. Exponential Decay Spatial Hysteresis
  4. Adaptive Section-Based Criticality Thresholds
  5. Decision Confidence Scoring & Explainability Traces (tc.v1 SOTA)
"""

from typing import List, Optional, Union, Dict, Any, Tuple
from collections import deque
import numpy as np

from ml.core.schema import (
    CalibratedSignal,
    SegmentDecision,
    SegmentSignals,
    DecisionType,
    Decision,
    DefectClass,
    SignalType,
    DefectFamily,
    SeverityLevel,
    Severity,
    ExplainabilityTrace,
)
from ml.fusion.hysteresis import ExponentialHysteresis


class ConfidenceWeightedFusion:
    """
    Computes a weighted consensus confidence score from active model streams.
    Physics (1.2) is weighted highest due to deterministic safety criticality.
    """

    def __init__(self):
        self.weights: Dict[SignalType, float] = {
            SignalType.VISUAL_KNOWN: 1.0,
            SignalType.VISUAL_NOVEL: 0.8,
            SignalType.GEOMETRY_KNOWN: 1.2,
            SignalType.GEOMETRY_KNOWN_TYPE: 0.9,
            SignalType.GEOMETRY_NOVEL: 0.7,
        }

    def compute_weighted_score(self, signals: SegmentSignals) -> float:
        total_weight = 0.0
        weighted_sum = 0.0

        for sig_type, weight in self.weights.items():
            sig = signals.get_primary(sig_type)
            if sig and sig.fired:
                weighted_sum += sig.value * weight
                total_weight += weight

        if total_weight == 0.0:
            return 0.0
        return float(weighted_sum / total_weight)


class AdaptiveThresholdManager:
    """Manages section-dependent operating thresholds and hysteresis decay rates."""

    def __init__(self):
        self.section_profiles: Dict[str, Dict[str, float]] = {
            "mainline_high_speed": {"threshold": 0.40, "decay_rate": 0.80, "known_threshold": 0.50},
            "mainline_standard": {"threshold": 0.50, "decay_rate": 0.70, "known_threshold": 0.60},
            "yard_track": {"threshold": 0.70, "decay_rate": 0.50, "known_threshold": 0.70},
            "siding": {"threshold": 0.80, "decay_rate": 0.50, "known_threshold": 0.75},
        }

    def get_profile(self, section_type: str) -> Dict[str, float]:
        return self.section_profiles.get(section_type, self.section_profiles["mainline_standard"])


def compute_cross_modal_boost(signals: SegmentSignals) -> float:
    """
    Calculates severity / confidence multiplier based on cross-modal corroboration:
      - Vision + Geometry active -> 1.5x (50% boost)
      - Single modality active -> 1.0x
      - Neither -> 0.0x
    """
    vision_fired = (
        signals.get_primary(SignalType.VISUAL_KNOWN).fired
        or signals.get_primary(SignalType.VISUAL_NOVEL).fired
    )
    geometry_fired = (
        signals.get_primary(SignalType.GEOMETRY_KNOWN).fired
        or signals.get_primary(SignalType.GEOMETRY_KNOWN_TYPE).fired
        or signals.get_primary(SignalType.GEOMETRY_FAULT_TYPE).fired
        or signals.get_primary(SignalType.GEOMETRY_NOVEL).fired
    )

    if vision_fired and geometry_fired:
        return 1.5
    elif vision_fired or geometry_fired:
        return 1.0
    return 0.0


class TrackChainFusionEngine:
    """
    SOTA Multi-Modal Railway Decision Engine unifying YOLOv8, PatchCore,
    EN 13848 Physics, Bi-LSTM Attention, and Sequence VAE.
    """

    def __init__(
        self,
        persistence_window: int = 3,
        known_threshold: float = 0.60,
        novel_threshold: float = 0.50,
        hysteresis_decay: float = 0.70,
    ):
        self.persistence_window = persistence_window
        self.known_threshold = known_threshold
        self.novel_threshold = novel_threshold

        self.weighted_fusion = ConfidenceWeightedFusion()
        self.threshold_manager = AdaptiveThresholdManager()
        self.hysteresis = ExponentialHysteresis(decay_rate=hysteresis_decay, threshold=novel_threshold, alpha=0.3)
        self.history = deque(maxlen=persistence_window)

    def reset(self):
        self.hysteresis.reset()
        self.history.clear()

    def fuse(
        self,
        signals: Union[SegmentSignals, List[CalibratedSignal]],
        window_id: str = "win-00000",
        start_chainage_m: float = 0.0,
        end_chainage_m: float = 0.0,
        section_type: str = "mainline_standard",
    ) -> SegmentDecision:
        """
        Fuses multi-modal signals into an actionable, explainable SegmentDecision.
        """
        profile = self.threshold_manager.get_profile(section_type)
        novel_thresh = profile.get("threshold", self.novel_threshold)
        known_thresh = profile.get("known_threshold", self.known_threshold)
        self.hysteresis.threshold = novel_thresh

        # 1. Normalize into SegmentSignals
        if isinstance(signals, SegmentSignals):
            seg_signals = signals
            all_sigs = signals.all_signals
        elif isinstance(signals, list):
            all_sigs = signals
            seg_signals = SegmentSignals(
                v_known=[s for s in all_sigs if s.signal_type == SignalType.VISUAL_KNOWN],
                v_novel=[s for s in all_sigs if s.signal_type == SignalType.VISUAL_NOVEL],
                g_known=[s for s in all_sigs if s.signal_type == SignalType.GEOMETRY_KNOWN],
                g_type=[s for s in all_sigs if s.signal_type in (SignalType.GEOMETRY_KNOWN_TYPE, SignalType.GEOMETRY_FAULT_TYPE)],
                g_novel=[s for s in all_sigs if s.signal_type == SignalType.GEOMETRY_NOVEL],
            )
        else:
            all_sigs = []
            seg_signals = SegmentSignals()

        # 2. Extract Primary Signals
        yolo = seg_signals.get_primary(SignalType.VISUAL_KNOWN)
        patch = seg_signals.get_primary(SignalType.VISUAL_NOVEL)
        phys = seg_signals.get_primary(SignalType.GEOMETRY_KNOWN)
        bilstm = seg_signals.get_primary(SignalType.GEOMETRY_KNOWN_TYPE)
        vae = seg_signals.get_primary(SignalType.GEOMETRY_NOVEL)

        # 3. Compute Cross-Modal Corroboration & Weighted Score
        cross_boost = compute_cross_modal_boost(seg_signals)
        weighted_conf = self.weighted_fusion.compute_weighted_score(seg_signals)

        # Build explainability traces
        traces: List[ExplainabilityTrace] = []
        for s in all_sigs:
            attn_p = s.metadata.get("attention_peak_bin")
            recon_e = s.metadata.get("reconstruction_error")
            traces.append(
                ExplainabilityTrace(
                    model_name=s.stream_name,
                    signal_type=s.signal_type,
                    raw_score=s.raw_score,
                    calibrated_score=s.calibrated_prob,
                    threshold=s.threshold,
                    fired=s.is_anomaly,
                    attention_peak=attn_p,
                    reconstruction_error=recon_e,
                )
            )

        # 4. Known Fault Rule Cascade (Immediate Deterministic Trigger)
        if phys.fired and phys.calibrated_prob >= known_thresh:
            if bilstm.fired and bilstm.label not in (DefectClass.NORMAL, None):
                primary_label = bilstm.label
                if bilstm.label in (DefectClass.DIPPED_JOINT, DefectClass.TWIST_FAULT, DefectClass.ALIGNMENT_KINK):
                    sev = SeverityLevel.CRITICAL if cross_boost > 1.0 else SeverityLevel.HIGH
                else:
                    sev = SeverityLevel.HIGH if cross_boost > 1.0 else SeverityLevel.MEDIUM
                source = "physics_bilstm"
            else:
                primary_label = phys.predicted_class or DefectClass.TWIST_EXCEEDANCE
                sev = SeverityLevel.HIGH if (phys.calibrated_prob >= 0.70 or cross_boost > 1.0) else SeverityLevel.MEDIUM
                source = "physics"

            conf = min(1.0, max(phys.calibrated_prob, bilstm.calibrated_prob) * (1.0 + 0.1 * (cross_boost - 1.0)))
            self.hysteresis.update(False, 0.0)
            self.history.append(DecisionType.INSPECT_KNOWN)

            return SegmentDecision(
                decision=DecisionType.INSPECT_KNOWN,
                primary_fault=primary_label,
                severity=sev,
                window_id=window_id,
                start_chainage_m=start_chainage_m,
                end_chainage_m=end_chainage_m,
                confidence=conf,
                defect_family=DefectFamily.GEOMETRY,
                signals=all_sigs,
                source=source,
                cross_modal_boost=cross_boost,
                traces=traces,
            )

        if yolo.fired and yolo.calibrated_prob >= known_thresh:
            primary_label = yolo.predicted_class or DefectClass.MISSING_FASTENER
            if yolo.predicted_class in (DefectClass.MISSING_FASTENER, DefectClass.CRACK):
                sev = SeverityLevel.CRITICAL if cross_boost > 1.0 else SeverityLevel.HIGH
            else:
                sev = SeverityLevel.HIGH if cross_boost > 1.0 else SeverityLevel.MEDIUM

            conf = min(1.0, yolo.calibrated_prob * (1.0 + 0.1 * (cross_boost - 1.0)))
            self.hysteresis.update(False, 0.0)
            self.history.append(DecisionType.INSPECT_KNOWN)

            return SegmentDecision(
                decision=DecisionType.INSPECT_KNOWN,
                primary_fault=primary_label,
                severity=sev,
                window_id=window_id,
                start_chainage_m=start_chainage_m,
                end_chainage_m=end_chainage_m,
                confidence=conf,
                defect_family=DefectFamily.VISUAL_COMPONENT,
                signals=all_sigs,
                source="yolo",
                cross_modal_boost=cross_boost,
                traces=traces,
            )

        # 5. Novel Anomaly Cascade with Exponential Hysteresis Persistence
        novel_active = bool(patch.fired or vae.fired)
        current_novel_conf = max(patch.calibrated_prob if patch.fired else 0.0, vae.calibrated_prob if vae.fired else 0.0)

        if self.persistence_window <= 1:
            is_persisted = bool(novel_active and current_novel_conf >= novel_thresh)
        else:
            is_persisted = bool(self.hysteresis.update(novel_active, current_novel_conf) and self.hysteresis.get_score() >= novel_thresh)

        if is_persisted:
            if patch.fired and vae.fired:
                primary_label = DefectClass.UNCLASSIFIED
                source = "patchcore_and_vae"
                conf = max(patch.calibrated_prob, vae.calibrated_prob)
            elif patch.fired:
                primary_label = DefectClass.VISUAL_ANOMALY
                source = "patchcore"
                conf = patch.calibrated_prob
            else:
                primary_label = DefectClass.GEOMETRY_ANOMALY
                source = "seq_vae"
                conf = vae.calibrated_prob

            sev = SeverityLevel.HIGH if (conf >= 0.80 or cross_boost > 1.0) else SeverityLevel.MEDIUM
            self.history.append(DecisionType.INSPECT_NOVEL)

            return SegmentDecision(
                decision=DecisionType.INSPECT_NOVEL,
                primary_fault=primary_label,
                severity=sev,
                window_id=window_id,
                start_chainage_m=start_chainage_m,
                end_chainage_m=end_chainage_m,
                confidence=conf,
                defect_family=DefectFamily.NOVEL_ANOMALY,
                signals=all_sigs,
                source=source,
                cross_modal_boost=cross_boost,
                traces=traces,
            )

        # 6. Nominal Clean Track
        self.history.append(DecisionType.OK)
        return SegmentDecision(
            decision=DecisionType.OK,
            primary_fault=DefectClass.NORMAL,
            severity=SeverityLevel.NORMAL,
            window_id=window_id,
            start_chainage_m=start_chainage_m,
            end_chainage_m=end_chainage_m,
            confidence=0.98,
            defect_family=DefectFamily.VISUAL_COMPONENT,
            signals=all_sigs,
            source="fusion",
            cross_modal_boost=1.0,
            traces=traces,
        )


# Backwards compatibility alias
PersistenceRuleFusion = TrackChainFusionEngine
