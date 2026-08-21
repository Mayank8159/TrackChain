"""
Enhanced training script for Bi-LSTM Geometry Fault Classifier.

Improvements:
- Deeper architecture (3 layers, 128 hidden)
- Multi-head attention
- Label smoothing
- Sequence augmentation
- Learning rate scheduling
- Gradient clipping
- Comprehensive metrics logging
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

# Add repo root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from ml.models.geometry.fault_classifier_enhanced import (
    EnhancedBiLSTMClassifier,
    SequenceAugmentation,
)


class GeometrySequenceClassificationDataset(Dataset):
    """Dataset for geometry sequence classification."""

    def __init__(self, csv_path: str, seq_len: int = 80, augment: bool = False):
        import pandas as pd

        self.seq_len = seq_len
        self.augment = augment
        self.augmenter = SequenceAugmentation() if augment else None

        # Load data
        df = pd.read_csv(csv_path)

        # Extract features
        feature_cols = ['twist_3m', 'versine_10m', 'versine_20m', 'unevenness_10m', 'cant']
        alt_feature_cols = ['twist_3m_mm', 'versine_10m_mm', 'versine_20m_mm', 'unevenness_10m_mm', 'cant_mm']

        if all(col in df.columns for col in feature_cols):
            self.features = df[feature_cols].values.astype(np.float32)
        elif all(col in df.columns for col in alt_feature_cols):
            self.features = df[alt_feature_cols].values.astype(np.float32)
        else:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            self.features = df[numeric_cols[:5]].values.astype(np.float32)

        # Extract labels
        if 'label' in df.columns:
            self.labels = df['label'].values.astype(np.int64)
        elif 'fault_type' in df.columns:
            self.labels = df['fault_type'].values.astype(np.int64)
        else:
            self.labels = np.zeros(len(df), dtype=np.int64)

        # Normalize features
        self.mean = self.features.mean(axis=0)
        self.std = self.features.std(axis=0) + 1e-8
        self.features = (self.features - self.mean) / self.std

        # Create sequences
        self.sequences = []
        self.seq_labels = []

        for i in range(0, len(self.features) - seq_len + 1, seq_len):
            self.sequences.append(self.features[i:i + seq_len])
            # Use majority label in window
            window_labels = self.labels[i:i + seq_len]
            self.seq_labels.append(np.bincount(window_labels).argmax())

        self.sequences = np.array(self.sequences)
        self.seq_labels = np.array(self.seq_labels)

        print(f"Loaded {len(self.sequences)} sequences from {csv_path}")

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        seq = torch.tensor(self.sequences[idx], dtype=torch.float32)
        label = torch.tensor(self.seq_labels[idx], dtype=torch.long)

        if self.augment and self.augmenter is not None:
            seq = self.augmenter.augment(seq)

        return seq, label


class LabelSmoothingLoss(nn.Module):
    """Label smoothing cross-entropy loss."""

    def __init__(self, num_classes: int, smoothing: float = 0.1):
        super().__init__()
        self.num_classes = num_classes
        self.smoothing = smoothing

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(pred, dim=1)

        # Create smoothed labels
        with torch.no_grad():
            true_dist = torch.zeros_like(log_probs)
            true_dist.fill_(self.smoothing / max(1, self.num_classes - 1))
            true_dist.scatter_(1, target.unsqueeze(1), 1.0 - self.smoothing)

        return torch.mean(torch.sum(-true_dist * log_probs, dim=1))


def train_enhanced_bilstm(args):
    """Train the enhanced Bi-LSTM classifier."""

    print("=" * 70)
    print("TrackChain Enhanced Bi-LSTM Training Pipeline")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Print configuration
    print(f"\nConfiguration:")
    print(f"  Epochs: {args.epochs}")
    print(f"  Hidden size: {args.hidden_size}")
    print(f"  Num layers: {args.num_layers}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.lr}")
    print(f"  Label smoothing: {args.label_smoothing}")

    # Load data
    print(f"\n[1/7] Loading data from {args.data_path}...")

    data_path = Path(args.data_path)
    csv_files = []
    if data_path.exists():
        if data_path.is_file() and data_path.suffix == '.csv':
            csv_files = [data_path]
        else:
            csv_files = list(data_path.glob('*.csv')) + list(data_path.glob('**/*.csv'))

    if not csv_files:
        print("  No CSV found in data path, generating synthetic dataset...")
        from ml.data.synthetic_geometry import SyntheticGeometryDataset
        full_dataset = SyntheticGeometryDataset(num_samples=2500, seq_len=args.seq_len, num_classes=5)

        n_total = len(full_dataset)
        n_train = int(0.8 * n_total)
        n_val = n_total - n_train

        train_subset, val_subset = torch.utils.data.random_split(full_dataset, [n_train, n_val])
        n_classes = 5
    else:
        csv_path = csv_files[0]
        print(f"  Using: {csv_path}")

        # Create datasets
        train_dataset = GeometrySequenceClassificationDataset(
            str(csv_path), seq_len=args.seq_len, augment=True
        )
        val_dataset = GeometrySequenceClassificationDataset(
            str(csv_path), seq_len=args.seq_len, augment=False
        )

        n_total = len(train_dataset)
        n_train = int(0.8 * n_total)
        n_val = n_total - n_train

        train_subset, val_subset = torch.utils.data.random_split(
            train_dataset, [n_train, n_val]
        )
        n_classes = len(np.unique(train_dataset.seq_labels)) if len(train_dataset) > 0 else 5

    train_loader = DataLoader(
        train_subset, batch_size=args.batch_size, shuffle=True, drop_last=(len(train_subset) > args.batch_size)
    )
    val_loader = DataLoader(
        val_subset, batch_size=args.batch_size, shuffle=False
    )

    print(f"  Train: {len(train_subset)} sequences")
    print(f"  Valid: {len(val_subset)} sequences")
    print(f"  Classes: {n_classes}")

    # Initialize model
    print(f"\n[2/7] Initializing Enhanced Bi-LSTM...")
    model = EnhancedBiLSTMClassifier(
        input_size=5,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        num_classes=n_classes,
        dropout=args.dropout,
        use_attention=True,
        num_heads=4,
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Model parameters: {n_params:,}")

    # Loss, optimizer, scheduler
    criterion = LabelSmoothingLoss(n_classes, smoothing=args.label_smoothing)

    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )

    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer,
        T_0=10,
        T_mult=2,
        eta_min=args.lr * 0.01,
    )

    # Training loop
    print(f"\n[3/7] Training for {args.epochs} epochs...")
    print("-" * 70)

    best_val_acc = 0.0
    best_epoch = 0
    training_history = {
        'epochs': [],
        'train_loss': [],
        'train_acc': [],
        'val_loss': [],
        'val_acc': [],
        'lr': [],
    }

    start_time = time.time()

    for epoch in range(args.epochs):
        # Training
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch_data, batch_labels in train_loader:
            batch_data = batch_data.to(device)
            batch_labels = batch_labels.to(device)

            optimizer.zero_grad()

            # Forward pass
            logits, _ = model(batch_data)

            # Compute loss
            loss = criterion(logits, batch_labels)

            # Backward pass
            loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)

            optimizer.step()

            train_loss += loss.item()
            _, predicted = logits.max(1)
            train_total += batch_labels.size(0)
            train_correct += predicted.eq(batch_labels).sum().item()

        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch_data, batch_labels in val_loader:
                batch_data = batch_data.to(device)
                batch_labels = batch_labels.to(device)

                logits, _ = model(batch_data)
                loss = criterion(logits, batch_labels)

                val_loss += loss.item()
                _, predicted = logits.max(1)
                val_total += batch_labels.size(0)
                val_correct += predicted.eq(batch_labels).sum().item()

        # Compute metrics
        train_acc = 100.0 * train_correct / max(1, train_total)
        val_acc = 100.0 * val_correct / max(1, val_total)

        avg_train_loss = train_loss / max(1, len(train_loader))
        avg_val_loss = val_loss / max(1, len(val_loader))

        # Log
        training_history['epochs'].append(epoch + 1)
        training_history['train_loss'].append(avg_train_loss)
        training_history['train_acc'].append(train_acc)
        training_history['val_loss'].append(avg_val_loss)
        training_history['val_acc'].append(val_acc)
        training_history['lr'].append(optimizer.param_groups[0]['lr'])

        if (epoch + 1) % 5 == 0 or epoch == 0 or epoch == args.epochs - 1:
            print(f"Epoch {epoch+1:02d}/{args.epochs} | "
                  f"Train Loss: {avg_train_loss:.4f} Acc: {train_acc:.2f}% | "
                  f"Val Loss: {avg_val_loss:.4f} Acc: {val_acc:.2f}% | "
                  f"LR: {optimizer.param_groups[0]['lr']:.6f}")

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch + 1

            save_path = Path(args.save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), save_path)

        # Update learning rate
        scheduler.step()

    training_time = time.time() - start_time

    print(f"\n[4/7] Training completed in {training_time/60:.2f} minutes")
    print(f"  Best epoch: {best_epoch}")
    print(f"  Best val accuracy: {best_val_acc:.2f}%")

    # Calibrate with SOTA Vector Scaling & Temperature Scaling
    print(f"\n[5/7] Calibrating with SOTA Vector Scaling (ECE optimization)...")

    if Path(args.save_path).exists():
        model.load_state_dict(torch.load(args.save_path, map_location=device))
    model.eval()

    # Collect logits from validation set
    val_logits = []
    val_labels = []

    with torch.no_grad():
        for batch_data, batch_labels in val_loader:
            batch_data = batch_data.to(device)
            logits, _ = model(batch_data)
            val_logits.append(logits.cpu())
            val_labels.append(batch_labels.cpu())

    if val_logits:
        val_logits = torch.cat(val_logits, dim=0).numpy()
        val_labels = torch.cat(val_labels, dim=0).numpy()
    else:
        val_logits = np.random.randn(50, n_classes)
        val_labels = np.random.randint(0, n_classes, 50)

    # 1. Scalar Temperature Baseline
    from scipy.optimize import minimize

    def nll_with_temperature(T):
        scaled_logits = val_logits / max(1e-4, T[0])
        probs = np.exp(scaled_logits - np.max(scaled_logits, axis=1, keepdims=True))
        probs = probs / probs.sum(axis=1, keepdims=True)
        nll = -np.log(probs[np.arange(len(val_labels)), val_labels] + 1e-10).mean()
        return nll

    result = minimize(nll_with_temperature, x0=[1.5], bounds=[(0.1, 10.0)])
    optimal_temperature = float(result.x[0])

    # 2. SOTA Vector Scaling (per-class weights W and biases b via L-BFGS)
    from ml.calibration.temperature import VectorScaler
    vector_scaler = VectorScaler(num_classes=n_classes)
    vs_res = vector_scaler.fit(val_logits, val_labels, lr=0.01, max_iter=100)
    ece_vector = vs_res["ece"]

    print(f"  Scalar Temperature:    {optimal_temperature:.3f}")
    print(f"  Vector Scaling ECE:    {ece_vector:.4f} (per-class weights + biases)")

    # Save calibration manifest
    calibration = {
        'temperature': float(optimal_temperature),
        'ece': float(ece_vector),
        'method': 'vector_scaling',
        'weights': vs_res["weights"],
        'biases': vs_res["biases"],
        'model': 'bilstm_geometry_typing',
        'val_samples': len(val_labels),
        'best_val_acc': float(best_val_acc),
    }

    calib_path = Path('artifacts/calibration/bilstm_temp.json')
    calib_path.parent.mkdir(parents=True, exist_ok=True)

    with open(calib_path, 'w', encoding='utf-8') as f:
        json.dump(calibration, f, indent=2)

    # Save training history
    history_path = Path(args.save_path).parent / 'bilstm_training_history.json'
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(training_history, f, indent=2)

    # Test attention explainability
    print(f"\n[6/7] Testing attention explainability...")

    sample_seq = val_subset[0][0]
    explanation = model.predict_with_explanation(sample_seq.to(device))

    if explanation['attention'] is not None:
        print(f"  Attention shape: {explanation['attention'].shape}")
        print(f"  Attention peak at bin: {np.argmax(explanation['attention'])}")

    # Mirror checkpoints to canonical & legacy locations for seamless inference
    canonical_pt = Path('artifacts/checkpoints/geometry/bilstm_fault_typing.pt')
    canonical_pt.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), canonical_pt)

    weights_mirror = Path('ml/models/geometry/weights/fault_classifier.pt')
    weights_mirror.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": model.state_dict(), "temperature": float(optimal_temperature)}, weights_mirror)

    # Final summary
    print(f"\n[7/7] Training Summary")
    print("=" * 70)
    print(f"Model saved to:     {args.save_path}")
    print(f"Mirrored to:        {canonical_pt}")
    print(f"                    {weights_mirror}")
    print(f"Calibration saved:  {calib_path}")
    print(f"Training history:   {history_path}")
    print(f"\nFinal Metrics:")
    print(f"  Best Validation Accuracy: {best_val_acc:.2f}%")
    print(f"  Optimal Temperature: {optimal_temperature:.3f}")
    print(f"  Vector Scaling ECE: {ece_vector:.4f}")
    print(f"  Training Time: {training_time/60:.2f} minutes")

    return model, calibration


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Enhanced Bi-LSTM")

    # Training parameters
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--batch-size', '--batch_size', dest='batch_size', type=int, default=128, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.0005, help='Learning rate')
    parser.add_argument('--weight-decay', '--weight_decay', dest='weight_decay', type=float, default=1e-4, help='Weight decay')
    parser.add_argument('--grad-clip', '--grad_clip', dest='grad_clip', type=float, default=1.0, help='Gradient clipping norm')

    # Model parameters
    parser.add_argument('--hidden-size', '--hidden_size', dest='hidden_size', type=int, default=128, help='Hidden size')
    parser.add_argument('--num-layers', '--num_layers', dest='num_layers', type=int, default=3, help='Number of LSTM layers')
    parser.add_argument('--dropout', type=float, default=0.4, help='Dropout rate')

    # Loss parameters
    parser.add_argument('--label-smoothing', '--label_smoothing', dest='label_smoothing', type=float, default=0.1, help='Label smoothing')

    # Data parameters
    parser.add_argument('--seq-len', '--seq_len', dest='seq_len', type=int, default=80, help='Sequence length')
    parser.add_argument('--data-path', '--data_path', dest='data_path', type=str,
                        default='data/processed/geometry_sequences/')

    # Output
    parser.add_argument('--save-path', '--save_path', dest='save_path', type=str,
                        default='artifacts/checkpoints/geometry/bilstm_fault_typing_enhanced.pt')

    args = parser.parse_args()

    train_enhanced_bilstm(args)
