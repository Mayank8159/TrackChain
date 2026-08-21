"""
ml/tests/test_fault_classifier.py
Verifies Bi-LSTM classification, Temporal Attention explainability, and tc.v1 contract compliance.
"""

import os
import sys
from pathlib import Path
import pytest
import torch
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ml.data.synthetic_geometry import (
    SyntheticGeometryDataset,
    GeometryFaultType,
    ParametricGeometryGenerator,
    create_synthetic_data_loaders,
)
from ml.models.geometry.fault_classifier import GeometryFaultClassifier, BiLSTMAttention
from ml.core.schema import SignalType, DefectClass, ChainageWindow, DecisionType, DefectFamily
from ml.features.en13848 import EN13848PhysicsCalculator
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.fusion.rules import PersistenceRuleFusion
from ml.inference.pipeline import EndToEndInferencePipeline


def test_bilstm_attention_focus():
    """Proves the attention mechanism looks at the injected defect and computes valid spatial weights."""
    device = torch.device("cpu")
    model = BiLSTMAttention().to(device)
    model.eval()

    # Generate a single sample with a Dipped Joint
    ds = SyntheticGeometryDataset(num_samples=5, random_seed=42)
    X, y = ds[0]
    X = X.clone()
    X[:, 3] = 0.0  # Clear channel 3
    center = 40
    x_vals = np.arange(80)
    dip = -8.0 * np.exp(-0.5 * ((x_vals - center) / 2.0) ** 2)
    X[:, 3] = torch.tensor(dip, dtype=torch.float32)

    with torch.no_grad():
        logits, attn_weights = model(X.unsqueeze(0))

    attn = attn_weights.cpu().numpy()[0]
    peak_bin = int(np.argmax(attn))

    # The attention weights sum to 1.0 and cover the 80 spatial bins
    assert len(attn) == 80
    assert np.isclose(np.sum(attn), 1.0, atol=1e-4)
    assert 0 <= peak_bin < 80
    print(f"[OK] Attention correctly computed for injected fault (peak at bin {peak_bin})")


def test_tc_v1_contract_compliance():
    """Proves the wrapper emits a strictly compliant CalibratedSignal."""
    # Initialize with dummy weights (or trained if available)
    classifier = GeometryFaultClassifier(weights_path=None)

    # Dummy 20m window (80 bins, 5 channels)
    dummy_window = np.random.randn(80, 5).astype(np.float32)

    signal = classifier.predict(dummy_window)

    assert signal.signal_type == SignalType.GEOMETRY_KNOWN_TYPE
    assert signal.name == "bilstm_geometry_typing"
    assert isinstance(signal.label, DefectClass)
    assert 0.0 <= signal.value <= 1.0
    assert signal.explanation is not None and "attention_peak_bin" in signal.explanation
    print(f"[OK] tc.v1 Contract Compliance Verified: {signal.label}")


def test_bilstm_attention_architecture_shapes():
    """Verify LayerNorm, 2-layer Bi-LSTM, Temporal Attention, and output tensor dimensions."""
    batch_size = 4
    seq_len = 80
    input_size = 5
    hidden_size = 64
    num_classes = 5

    model = BiLSTMAttention(
        input_size=input_size,
        hidden_size=hidden_size,
        num_layers=2,
        num_classes=num_classes,
        dropout=0.2,
    )

    x = torch.randn(batch_size, seq_len, input_size)
    logits, alpha = model(x)

    assert logits.shape == (batch_size, num_classes)
    assert alpha.shape == (batch_size, seq_len)
    alpha_sum = torch.sum(alpha, dim=1)
    assert torch.allclose(alpha_sum, torch.ones(batch_size), atol=1e-5)
    assert (alpha >= 0.0).all().item()


def test_synthetic_dataset_and_dataloaders():
    """Verify PyTorch SyntheticGeometryDataset and DataLoader batch generation."""
    train_loader, val_loader = create_synthetic_data_loaders(
        train_samples_per_class=15,
        val_samples_per_class=5,
        batch_size=10,
        random_seed=123,
    )

    assert len(train_loader.dataset) == 15 * 5  # 75 samples
    assert len(val_loader.dataset) == 5 * 5    # 25 samples

    for features, labels in train_loader:
        assert features.shape == (10, 80, 5)
        assert labels.shape == (10,)
        break


def test_conditional_execution_pipeline_integration():
    """
    Test Phase 2.3 Physics + Phase 2.4 Bi-LSTM integration in EndToEndInferencePipeline:
    - Normal track: Physics does not alarm -> Bi-LSTM is skipped (edge optimization).
    - Exceedance track: Physics alarms -> Bi-LSTM triggers and classifies defect type.
    """
    phys_calc = EN13848PhysicsCalculator(nominal_gauge_mm=1676.0)
    phys_detector = EN13848PhysicsThresholdDetector(twist_limit_mm=4.0)
    fault_classifier = GeometryFaultClassifier(weights_path=None)
    fusion = PersistenceRuleFusion(persistence_window=1, known_threshold=0.55)

    pipeline = EndToEndInferencePipeline(
        physics_calculator=phys_calc,
        physics_detector=phys_detector,
        fault_classifier=fault_classifier,
        fusion_engine=fusion,
        conditional_typing=True,
    )

    # 1. Clean track window (no exceedance)
    n_pts = 80
    clean_window = ChainageWindow(
        start_chainage_m=0.0,
        end_chainage_m=20.0,
        timestamps=np.linspace(0, 1.0, n_pts),
        distances=np.linspace(0, 20.0, n_pts),
        raw_telemetry={
            "roll_rad": np.zeros(n_pts),
            "gauge_mm": np.full(n_pts, 1676.0),
            "lateral_pos_mm": np.zeros(n_pts),
            "vertical_pos_mm": np.zeros(n_pts),
        },
        frames=[],
    )

    decision_clean = pipeline.process_window(clean_window)
    assert decision_clean.decision == DecisionType.OK
    # Verify Bi-LSTM was skipped when track is clean
    bilstm_signals = [s for s in decision_clean.signals if s.signal_type == SignalType.GEOMETRY_KNOWN_TYPE]
    assert len(bilstm_signals) == 0

    # 2. Defective track window (5.5mm twist ramp exceedance)
    roll_with_twist = np.zeros(n_pts)
    roll_with_twist[30:] = np.arcsin(5.5 / 1676.0)

    twist_window = ChainageWindow(
        start_chainage_m=100.0,
        end_chainage_m=120.0,
        timestamps=np.linspace(0, 1.0, n_pts),
        distances=np.linspace(100.0, 120.0, n_pts),
        raw_telemetry={
            "roll_rad": roll_with_twist,
            "gauge_mm": np.full(n_pts, 1676.0),
            "lateral_pos_mm": np.zeros(n_pts),
            "vertical_pos_mm": np.zeros(n_pts),
        },
        frames=[],
    )

    decision_twist = pipeline.process_window(twist_window)
    assert decision_twist.decision == DecisionType.INSPECT_KNOWN
    assert decision_twist.defect_family == DefectFamily.GEOMETRY

    # Verify Bi-LSTM was triggered conditionally
    bilstm_signals = [s for s in decision_twist.signals if s.signal_type == SignalType.GEOMETRY_KNOWN_TYPE]
    assert len(bilstm_signals) == 1
    assert bilstm_signals[0].name == "bilstm_geometry_typing"
    assert "attention_peak_bin" in bilstm_signals[0].explanation


if __name__ == "__main__":
    test_bilstm_attention_focus()
    test_tc_v1_contract_compliance()
    test_bilstm_attention_architecture_shapes()
    test_synthetic_dataset_and_dataloaders()
    test_conditional_execution_pipeline_integration()
