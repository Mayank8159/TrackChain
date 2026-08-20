# Train the Bi-LSTM geometry fault classifier.

import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from ml.models.geometry.fault_classifier import BiLSTMGeometryClassifier
from ml.data.synthetic import generate_synthetic_geometry
from ml.data.datasets import GeometrySequenceDataset
from ml.data.loaders import build_dataloaders
from ml.training.base_trainer import BaseTrainer
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("train_fault_classifier")


def train_geometry_classifier(epochs: int = 10):
    logger.info("Generating synthetic geometry sequence windows for Bi-LSTM training...")
    raw = generate_synthetic_geometry(length_m=5000.0)

    # Window into 100-step sequences
    seq_len = 100
    n_windows = len(raw["chainage_m"]) // seq_len
    features = np.stack([
        raw["gauge_mm"],
        raw["cant_mm"],
        raw["twist_mm_per_m"],
        raw["vertical_unevenness_mm"],
        raw["alignment_mm"],
        raw["vibration_rms_g"],
    ], axis=1)

    X = features[:n_windows * seq_len].reshape(n_windows, seq_len, 6)
    y = raw["fault_labels"][:n_windows * seq_len].reshape(n_windows, seq_len)[:, -1]

    dataset = GeometrySequenceDataset(X, y)
    train_loader, val_loader = build_dataloaders(dataset, batch_size=16)

    model = BiLSTMGeometryClassifier(input_dim=6, num_classes=4)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    trainer = BaseTrainer(model, optimizer, criterion)
    for epoch in range(epochs):
        train_loss = trainer.train_epoch(train_loader)
        val_loss = trainer.evaluate(val_loader)
        logger.info(f"Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")

    trainer.save_checkpoint("bilstm_geometry.pt")
    logger.info("Bi-LSTM checkpoint saved to artifacts/checkpoints/bilstm_geometry.pt")


if __name__ == "__main__":
    train_geometry_classifier()
