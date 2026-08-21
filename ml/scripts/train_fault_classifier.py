"""
ml/scripts/train_fault_classifier.py
Trains the Bi-LSTM Geometry Fault Classifier (tc.v1 SOTA).
"""

import os
import sys
import argparse
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ml.data.synthetic_geometry import SyntheticGeometryDataset
from ml.models.geometry.fault_classifier import BiLSTMAttention


def train(
    num_samples: int = 5000,
    val_samples: int = 1000,
    epochs: int = 20,
    batch_size: int = 64,
    lr: float = 1e-3,
    save_path: str = "artifacts/checkpoints/geometry/bilstm_fault_typing.pt",
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Data
    train_ds = SyntheticGeometryDataset(num_samples=num_samples)
    val_ds = SyntheticGeometryDataset(num_samples=val_samples)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    # 2. Model
    model = BiLSTMAttention().to(device)

    # 3. SOTA Loss & Optimizer
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    # 4. Training Loop
    print(f"Starting training for {epochs} epochs on {len(train_ds)} samples...")
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for X, y in train_loader:
            X, y = X.to(device), y.to(device)
            optimizer.zero_grad()
            logits, _ = model(X)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        scheduler.step()

        # Validation
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for X, y in val_loader:
                X, y = X.to(device), y.to(device)
                logits, _ = model(X)
                preds = torch.argmax(logits, dim=1)
                correct += (preds == y).sum().item()
                total += y.size(0)

        val_acc = correct / max(1, total)
        print(f"Epoch {epoch+1:02d}/{epochs:02d} | Loss: {train_loss/len(train_loader):.4f} | Val Acc: {val_acc * 100:.2f}%")

    # 5. Save Checkpoint
    out_dir = os.path.dirname(save_path)
    os.makedirs(out_dir, exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"[OK] Model saved to {save_path}")

    # Mirror to ml/models/geometry/weights for unified resolution
    mirror_path = "ml/models/geometry/weights/fault_classifier.pt"
    os.makedirs(os.path.dirname(mirror_path), exist_ok=True)
    torch.save({"model_state_dict": model.state_dict(), "temperature": 1.5}, mirror_path)
    print(f"[OK] Mirrored weights to {mirror_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Bi-LSTM Geometry Classifier.")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--batch_size", "--batch-size", "--batch", type=int, default=64, dest="batch_size", help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--save_path", "--save-path", default="artifacts/checkpoints/geometry/bilstm_fault_typing.pt", dest="save_path")
    parser.add_argument("--num_samples", "--num-samples", type=int, default=5000, dest="num_samples")
    args = parser.parse_args()

    train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        save_path=args.save_path,
        num_samples=args.num_samples,
    )
