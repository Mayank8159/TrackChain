# Training Pipeline for TrackChain Bi-LSTM Sequence Classifier with Temporal Attention (tc.v1 SOTA).

import os
import argparse
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path
import yaml
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR

from ml.models.geometry.fault_classifier import BiLSTMGeometryClassifier
from ml.data.synthetic_geometry import create_synthetic_data_loaders, CLASS_MAP
from ml.calibration.temperature import TemperatureScaler


def train_fault_classifier(
    epochs: int = 25,
    batch_size: int = 32,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    label_smoothing: float = 0.1,
    train_samples_per_class: int = 250,
    val_samples_per_class: int = 50,
    save_path: str = "ml/models/geometry/weights/fault_classifier.pt",
    config_path: str = "ml/configs/fault_classifier.yaml",
    device_name: str = "auto",
) -> Dict[str, Any]:
    """
    Trains the Bi-LSTM sequence classifier on parametric EN 13848 track geometry data.
    Fits post-hoc temperature scaling and saves production weights.
    """
    # 1. Device Setup
    if device_name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_name)
    print(f"[Train] Initializing training on device: {device}")

    # 2. Load Config if available
    cfg_file = Path(config_path)
    input_dim = 5
    hidden_dim = 64
    num_layers = 2
    dropout = 0.3
    num_classes = 6

    if cfg_file.exists():
        with open(cfg_file, "r") as f:
            cfg = yaml.safe_load(f) or {}
        input_dim = int(cfg.get("input_dim", input_dim))
        hidden_dim = int(cfg.get("hidden_dim", hidden_dim))
        num_layers = int(cfg.get("num_layers", num_layers))
        dropout = float(cfg.get("dropout", dropout))
        num_classes = int(cfg.get("num_classes", num_classes))

    # 3. Create Balanced DataLoaders
    print(f"[Train] Generating parametric synthetic dataset (EN 13848-2 Grade 4 PSD)...")
    train_loader, val_loader = create_synthetic_data_loaders(
        train_samples_per_class=train_samples_per_class,
        val_samples_per_class=val_samples_per_class,
        batch_size=batch_size,
    )
    print(f"        Train batches: {len(train_loader)} ({train_samples_per_class * num_classes} windows)")
    print(f"        Val batches:   {len(val_loader)} ({val_samples_per_class * num_classes} windows)")

    # 4. Model, Criterion, Optimizer & Scheduler
    model = BiLSTMGeometryClassifier(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        num_classes=num_classes,
        dropout=dropout,
    ).to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    # 5. Training Loop
    best_val_acc = 0.0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    print(f"[Train] Starting optimization ({epochs} epochs, Label Smoothing={label_smoothing}, AdamW)...")
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for features, labels, _ in train_loader:
            features = features.to(device)  # [B, 80, 5]
            labels = labels.to(device)      # [B]

            optimizer.zero_grad()
            logits = model(features)
            loss = criterion(logits, labels)
            loss.backward()

            # Gradient clipping for LSTM stability
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
            optimizer.step()

            running_loss += loss.item() * features.size(0)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        scheduler.step()
        epoch_train_loss = running_loss / max(1, total)
        epoch_train_acc = correct / max(1, total)

        # Validation Step
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for features, labels, _ in val_loader:
                features = features.to(device)
                labels = labels.to(device)
                logits = model(features)
                loss = criterion(logits, labels)
                val_loss += loss.item() * features.size(0)
                preds = torch.argmax(logits, dim=1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        epoch_val_loss = val_loss / max(1, val_total)
        epoch_val_acc = val_correct / max(1, val_total)

        history["train_loss"].append(epoch_train_loss)
        history["train_acc"].append(epoch_train_acc)
        history["val_loss"].append(epoch_val_loss)
        history["val_acc"].append(epoch_val_acc)

        if epoch % 5 == 0 or epoch == epochs or epoch == 1:
            print(
                f"  Epoch [{epoch:02d}/{epochs:02d}] "
                f"Train Loss: {epoch_train_loss:.4f} Acc: {epoch_train_acc * 100:.1f}% | "
                f"Val Loss: {epoch_val_loss:.4f} Acc: {epoch_val_acc * 100:.1f}%"
            )

    # 6. Temperature Calibration on Validation Set
    print("[Train] Calibrating network probabilities via Temperature Scaling (Platt)...")
    model.eval()
    val_logits_list = []
    val_labels_list = []

    with torch.no_grad():
        for features, labels, _ in val_loader:
            features = features.to(device)
            logits = model(features)
            val_logits_list.append(logits.cpu().numpy())
            val_labels_list.append(labels.cpu().numpy())

    all_val_logits = np.concatenate(val_logits_list, axis=0)
    all_val_labels = np.concatenate(val_labels_list, axis=0)

    scaler = TemperatureScaler()
    learned_temp = scaler.fit(all_val_logits, all_val_labels)
    print(f"        Optimal Temperature (T): {learned_temp:.4f}")

    # 7. Save Model & Calibration Weights
    save_p = Path(save_path)
    save_p.parent.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "temperature": learned_temp,
        "input_dim": input_dim,
        "hidden_dim": hidden_dim,
        "num_layers": num_layers,
        "num_classes": num_classes,
        "classes": CLASS_MAP,
        "metrics": {
            "final_train_acc": history["train_acc"][-1],
            "final_val_acc": history["val_acc"][-1],
            "final_val_loss": history["val_loss"][-1],
            "optimal_temperature": learned_temp,
        },
    }
    torch.save(checkpoint, save_p)
    print(f"[OK] Saved trained Bi-LSTM model checkpoint to: {save_p}")

    return {
        "checkpoint_path": str(save_p),
        "val_acc": history["val_acc"][-1],
        "temperature": learned_temp,
        "history": history,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Bi-LSTM track geometry fault classifier.")
    parser.add_argument("--epochs", type=int, default=25, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--train-samples", type=int, default=250, help="Train samples per class")
    parser.add_argument("--val-samples", type=int, default=50, help="Val samples per class")
    parser.add_argument("--save-path", default="ml/models/geometry/weights/fault_classifier.pt", help="Save checkpoint path")
    parser.add_argument("--config", default="ml/configs/fault_classifier.yaml", help="Configuration YAML path")
    args = parser.parse_args()

    train_fault_classifier(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        train_samples_per_class=args.train_samples,
        val_samples_per_class=args.val_samples,
        save_path=args.save_path,
        config_path=args.config,
    )
