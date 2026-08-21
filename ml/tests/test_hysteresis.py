"""
ml/tests/test_hysteresis.py
Validates Exponential Decay Spatial Hysteresis for noise rejection and defect continuity.
"""

import pytest

from ml.fusion.hysteresis import ExponentialHysteresis


def test_hysteresis_single_isolated_spike_suppression():
    """Verify that a single isolated spike doesn't exceed the 0.5 threshold with low confidence."""
    h = ExponentialHysteresis(decay_rate=0.7, threshold=0.5, alpha=0.3)

    # Step 1: Weak spike (confidence 0.4) -> Does not alarm
    alarm_1 = h.update(current_fired=True, current_confidence=0.4)
    assert alarm_1 is False
    assert pytest.approx(h.get_score(), rel=1e-3) == 0.12

    # Step 2: Next step is clean -> Decays to 0.084
    alarm_2 = h.update(current_fired=False, current_confidence=0.0)
    assert alarm_2 is False
    assert pytest.approx(h.get_score(), rel=1e-3) == 0.084


def test_hysteresis_sustained_evidence_accumulation():
    """Verify that sustained evidence across 3 consecutive windows accumulates and triggers alarm."""
    h = ExponentialHysteresis(decay_rate=0.7, threshold=0.5, alpha=0.3)

    # Window 1: confidence 0.85 -> score = 0.255 < 0.5
    alarm_1 = h.update(True, 0.85)
    assert alarm_1 is False

    # Window 2: confidence 0.85 -> score = 0.4335 < 0.5
    alarm_2 = h.update(True, 0.85)
    assert alarm_2 is False

    # Window 3: confidence 0.85 -> score = 0.55845 >= 0.5 -> ALARM
    alarm_3 = h.update(True, 0.85)
    assert alarm_3 is True
    assert pytest.approx(h.get_score(), rel=1e-3) == 0.55845


def test_hysteresis_noise_dropout_continuity():
    """Verify that a genuine multi-segment defect quickly recovers after a single dropout."""
    h = ExponentialHysteresis(decay_rate=0.7, threshold=0.5, alpha=0.3)

    # Build up alarm over 3 windows
    h.update(True, 0.85)
    h.update(True, 0.85)
    alarm_3 = h.update(True, 0.85)
    assert alarm_3 is True

    # Single dropout: score decays to 0.3909
    alarm_drop = h.update(False, 0.0)
    assert alarm_drop is False
    assert pytest.approx(h.get_score(), rel=1e-3) == 0.3909

    # Immediate return on next window: score jumps back to 0.5286 >= 0.5 (ALARM immediately restored!)
    alarm_return = h.update(True, 0.85)
    assert alarm_return is True
    assert pytest.approx(h.get_score(), rel=1e-3) == 0.52863
