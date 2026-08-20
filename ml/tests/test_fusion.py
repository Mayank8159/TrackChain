# Unit tests for rule fusion and persistence.

from ml.fusion.rules import PersistenceRuleFusion
from ml.core.schema import CalibratedSignal, DecisionType, DefectClass


def test_rule_fusion_nominal():
    fusion = PersistenceRuleFusion(persistence_window=1)
    signals = [
        CalibratedSignal(
            stream_name="vision_detector",
            raw_score=0.1,
            calibrated_prob=0.1,
            is_anomaly=False,
        )
    ]
    decision = fusion.fuse("win-1", 0.0, 25.0, signals)
    assert decision.decision == DecisionType.OK


def test_rule_fusion_known_fault():
    fusion = PersistenceRuleFusion(persistence_window=1)
    signals = [
        CalibratedSignal(
            stream_name="vision_detector",
            raw_score=0.9,
            calibrated_prob=0.92,
            predicted_class=DefectClass.CRACK,
            is_anomaly=True,
        )
    ]
    decision = fusion.fuse("win-2", 25.0, 50.0, signals)
    assert decision.decision == DecisionType.KNOWN
    assert decision.primary_fault == DefectClass.CRACK
