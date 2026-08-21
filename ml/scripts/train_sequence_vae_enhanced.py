"""
Enhanced training script for Sequence VAE.

Fixes:
- Accepts both --latent_dim and --latent-dim arguments
- KL annealing for stable training
- Learning rate scheduling
- Gradient clipping
- Comprehensive metrics logging
- Dual-path scoring calibration

Usage:
    python ml/scripts/train_sequence_vae_enhanced.py \
        --epochs 50 \
        --beta 0.01 \
        --latent-dim 16 \
        --batch-size 64 \
        --lr 0.001 \
        --save-path artifacts/checkpoints/geometry/sequence_vae_enhanced.pt
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

# Add repo root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from ml.models.geometry.sequence_vae_enhanced import EnhancedSequenceVAE


class GeometrySequenceDataset(Dataset):
    """Dataset for geometry sequences."""

    def __init__(self, csv_path: str, seq_len: int = 80, n_features: int = 5):
        import pandas as pd

        self.seq_len = seq_len
        self.n_features = n_features

        # Load data
        df = pd.read_csv(csv_path)

        # Extract features
        feature_cols = ['twist_3m', 'versine_10m', 'versine_20m', 'unevenness_10m', 'cant']
        alt_feature_cols = ['twist_3m_mm', 'versine_10m_mm', 'versine_20m_mm', 'unevenness_10m_mm', 'cant_mm']

        if all(col in df.columns for col in feature_cols):
            self.data = df[feature_cols].values.astype(np.float32)
        elif all(col in df.columns for col in alt_feature_cols):
            self.data = df[alt_feature_cols].values.astype(np.float32)
        else:
            # Fallback: use first n_features numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            self.data = df[numeric_cols[:n_features]].values.astype(np.float32)

        # Normalize
        self.mean = self.data.mean(axis=0)
        self.std = self.data.std(axis=0) + 1e-8
        self.data = (self.data - self.mean) / self.std

        # Create sequences
        self.sequences = []
        stride = max(1, seq_len // 2)
        for i in range(0, len(self.data) - seq_len + 1, stride):  # 50% overlap
            self.sequences.append(self.data[i:i + seq_len])

        self.sequences = np.array(self.sequences)

        # Filter to normal only (if labels available)
        if 'label' in df.columns and len(self.sequences) > 0:
            # Keep only normal sequences (label == 0)
            normal_mask = df['label'].values[:len(self.sequences)] == 0
            if normal_mask.sum() > 0:
                self.sequences = self.sequences[normal_mask]

        print(f"Loaded {len(self.sequences)} sequences from {csv_path}")

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return torch.tensor(self.sequences[idx], dtype=torch.float32)


def train_enhanced_vae(args):
    """Train the enhanced Sequence VAE."""

    print("=" * 70)
    print("TrackChain Enhanced Sequence VAE Training Pipeline")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Print configuration
    print(f"\nConfiguration:")
    print(f"  Epochs: {args.epochs}")
    print(f"  Beta: {args.beta}")
    print(f"  Latent dim: {args.latent_dim}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.lr}")
    print(f"  KL annealing: {args.kl_annealing}")
    print(f"  Annealing epochs: {args.annealing_epochs}")

    # Load data
    print(f"\n[1/6] Loading data from {args.data_path}...")

    # Find CSV file
    data_path = Path(args.data_path)
    csv_files = []
    if data_path.exists():
        if data_path.is_file() and data_path.suffix == '.csv':
            csv_files = [data_path]
        else:
            csv_files = list(data_path.glob('*.csv')) + list(data_path.glob('**/*.csv'))

    if not csv_files:
        # Generate synthetic data
        print("  No CSV found, generating synthetic data...")
        from ml.data.synthetic_geometry import SyntheticGeometryDataset
        dataset = SyntheticGeometryDataset(num_samples=3000, seq_len=args.seq_len)

        # Filter to normal only
        normal_indices = [i for i, (_, label) in enumerate(dataset) if label == 0]

        # Create sequences tensor
        sequences = []
        for i in normal_indices:
            seq, _ = dataset[i]
            sequences.append(seq.numpy() if hasattr(seq, 'numpy') else np.asarray(seq))

        sequences = np.array(sequences)
    else:
        csv_path = csv_files[0]
        print(f"  Using: {csv_path}")
        dataset = GeometrySequenceDataset(str(csv_path), seq_len=args.seq_len, n_features=args.n_features)
        sequences = dataset.sequences
        if len(sequences) == 0:
            print("  CSV sequence count was 0, falling back to synthetic data...")
            from ml.data.synthetic_geometry import SyntheticGeometryDataset
            synth_dataset = SyntheticGeometryDataset(num_samples=3000, seq_len=args.seq_len)
            normal_indices = [i for i, (_, label) in enumerate(synth_dataset) if label == 0]
            sequences = np.array([synth_dataset[i][0].numpy() for i in normal_indices])

    # Split into train and validation
    n_total = len(sequences)
    n_train = max(1, int(0.8 * n_total))

    train_sequences = sequences[:n_train]
    val_sequences = sequences[n_train:] if n_train < n_total else sequences[:max(1, int(0.2 * n_total))]

    print(f"  Train: {len(train_sequences)} sequences")
    print(f"  Valid: {len(val_sequences)} sequences")

    # Create data loaders
    train_loader = DataLoader(
        torch.utils.data.TensorDataset(torch.tensor(train_sequences, dtype=torch.float32)),
        batch_size=min(args.batch_size, len(train_sequences)),
        shuffle=True,
        drop_last=(len(train_sequences) > args.batch_size),
    )

    val_loader = DataLoader(
        torch.utils.data.TensorDataset(torch.tensor(val_sequences, dtype=torch.float32)),
        batch_size=min(args.batch_size, len(val_sequences)),
        shuffle=False,
    )

    # Initialize model
    print(f"\n[2/6] Initializing Enhanced Sequence VAE...")
    model = EnhancedSequenceVAE(
        seq_len=args.seq_len,
        n_features=args.n_features,
        latent_dim=args.latent_dim,
        beta=args.beta,
        use_kl_annealing=args.kl_annealing,
        annealing_epochs=args.annealing_epochs,
    ).to(device)

    # Count parameters
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Model parameters: {n_params:,}")

    # Optimizer and scheduler
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )

    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(1, args.epochs),
        eta_min=args.lr * 0.01,
    )

    # Training loop
    print(f"\n[3/6] Training for {args.epochs} epochs...")
    print("-" * 70)

    best_val_loss = float('inf')
    best_epoch = 0
    training_history = {
        'epochs': [],
        'train_loss': [],
        'train_recon': [],
        'train_kl': [],
        'val_loss': [],
        'val_recon': [],
        'val_kl': [],
        'lr': [],
        'beta': [],
    }

    start_time = time.time()

    for epoch in range(args.epochs):
        # Training
        model.train()
        train_total_loss = 0.0
        train_recon_loss = 0.0
        train_kl_loss = 0.0
        current_beta = 0.0

        for batch_idx, (batch_data,) in enumerate(train_loader):
            batch_data = batch_data.to(device)

            optimizer.zero_grad()

            # Forward pass
            recon_batch, mu, logvar = model(batch_data)

            # Compute loss with KL annealing
            losses = model.compute_loss(batch_data, recon_batch, mu, logvar, epoch)

            # Backward pass
            losses['total'].backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)

            optimizer.step()

            train_total_loss += losses['total'].item()
            train_recon_loss += losses['recon'].item()
            train_kl_loss += losses['kl'].item()
            current_beta = float(losses['beta'])

        # Validation
        model.eval()
        val_total_loss = 0.0
        val_recon_loss = 0.0
        val_kl_loss = 0.0

        with torch.no_grad():
            for (batch_data,) in val_loader:
                batch_data = batch_data.to(device)

                recon_batch, mu, logvar = model(batch_data)
                losses = model.compute_loss(batch_data, recon_batch, mu, logvar, epoch)

                val_total_loss += losses['total'].item()
                val_recon_loss += losses['recon'].item()
                val_kl_loss += losses['kl'].item()

        # Compute averages
        n_train_batches = max(1, len(train_loader))
        n_val_batches = max(1, len(val_loader))

        avg_train_loss = train_total_loss / n_train_batches
        avg_train_recon = train_recon_loss / n_train_batches
        avg_train_kl = train_kl_loss / n_train_batches

        avg_val_loss = val_total_loss / n_val_batches
        avg_val_recon = val_recon_loss / n_val_batches
        avg_val_kl = val_kl_loss / n_val_batches

        # Log
        training_history['epochs'].append(epoch + 1)
        training_history['train_loss'].append(avg_train_loss)
        training_history['train_recon'].append(avg_train_recon)
        training_history['train_kl'].append(avg_train_kl)
        training_history['val_loss'].append(avg_val_loss)
        training_history['val_recon'].append(avg_val_recon)
        training_history['val_kl'].append(avg_val_kl)
        training_history['lr'].append(optimizer.param_groups[0]['lr'])
        training_history['beta'].append(current_beta)

        # Print progress
        if (epoch + 1) % 5 == 0 or epoch == 0 or epoch == args.epochs - 1:
            print(f"Epoch {epoch+1:02d}/{args.epochs} | "
                  f"Train: {avg_train_loss:.4f} (R:{avg_train_recon:.4f} K:{avg_train_kl:.4f}) | "
                  f"Val: {avg_val_loss:.4f} (R:{avg_val_recon:.4f} K:{avg_val_kl:.4f}) | "
                  f"β:{current_beta:.4f} | "
                  f"LR:{optimizer.param_groups[0]['lr']:.6f}")

        # Save best model and check early stopping
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch + 1
            early_stopping_counter = 0

            save_path = Path(args.save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), save_path)
        else:
            early_stopping_counter += 1
            if early_stopping_counter >= getattr(args, 'patience', 8):
                print(f"\n[INFO] Early stopping triggered at epoch {epoch+1} (patience={args.patience} reached, best epoch: {best_epoch})")
                break

        # Update learning rate
        scheduler.step()

    training_time = time.time() - start_time

    print(f"\n[4/6] Training completed in {training_time/60:.2f} minutes")
    print(f"  Best epoch: {best_epoch}")
    print(f"  Best val loss: {best_val_loss:.4f}")

    # Fit latent distribution for Mahalanobis scoring
    print(f"\n[5/6] Fitting latent distribution for dual-path scoring...")
    if Path(args.save_path).exists():
        model.load_state_dict(torch.load(args.save_path, map_location=device))
    model.eval()

    # Use validation sequences for fitting (model handles device mapping internally)
    val_tensor = torch.tensor(val_sequences, dtype=torch.float32)
    model.fit_latent_distribution(val_tensor)

    print(f"  Latent mean shape: {model.latent_mean.shape}")
    print(f"  Latent covariance inverse shape: {model.latent_cov_inv.shape}")

    # Calibrate thresholds with Extreme Value Theory (EVT) and P99
    print(f"\n[6/6] Calibrating anomaly thresholds with Extreme Value Theory (EVT)...")

    # Compute reconstruction errors on validation set
    val_errors = []
    val_mahalanobis = []

    with torch.no_grad():
        for i in range(0, len(val_sequences), args.batch_size):
            batch = torch.tensor(val_sequences[i:i + args.batch_size], dtype=torch.float32).to(device)

            for sample_idx in range(batch.size(0)):
                scores = model.compute_anomaly_score(batch[sample_idx])
                val_errors.append(scores.get('recon_error', 0.0))
                val_mahalanobis.append(scores.get('mahalanobis_dist', 0.0))

    # Compute P99 thresholds
    p99_recon = float(np.percentile(val_errors, 99)) if val_errors else 1.0
    p99_mahalanobis = float(np.percentile(val_mahalanobis, 99)) if val_mahalanobis else 1.0
    ensemble_scores = [0.7 * e + 0.3 * m for e, m in zip(val_errors, val_mahalanobis)] if val_errors else [1.0]
    p99_ensemble = float(np.percentile(ensemble_scores, 99))

    # SOTA: Compute Extreme Value Theory (EVT) Peaks-Over-Threshold
    evt_recon = model.fit_evt_threshold(val_errors, target_fpr=0.01)
    evt_ensemble = model.fit_evt_threshold(ensemble_scores, target_fpr=0.01)

    # Empirical False Positive Rate (FPR) Validation Check (Upgrade B)
    actual_fpr = float(np.mean([s > evt_ensemble['threshold'] for s in ensemble_scores]))
    print(f"  P99 Ensemble Threshold:  {p99_ensemble:.4f}")
    print(f"  EVT Ensemble Threshold:  {evt_ensemble['threshold']:.4f} (shape={evt_ensemble['shape']:.4f}, scale={evt_ensemble['scale']:.4f})")
    print(f"  Empirical Validation FPR: {actual_fpr*100:.2f}% (Target: 1.00%, Tolerance <= 2.00%)")
    assert actual_fpr <= 0.02, f"FPR validation check failed: {actual_fpr:.4f} > 0.02"

    # Strict Normalization Guard Check (Upgrade C)
    model.threshold_evt = float(evt_ensemble['threshold'])
    test_prob_min = model.score_to_probability(0.0)
    test_prob_thresh = model.score_to_probability(evt_ensemble['threshold'])
    test_prob_extreme = model.score_to_probability(evt_ensemble['threshold'] * 5.0)
    assert 0.0 <= test_prob_min <= 0.20, f"Min score probability out of expected range: {test_prob_min}"
    assert abs(test_prob_thresh - 0.50) < 0.01, f"Threshold decision boundary not 0.50: {test_prob_thresh}"
    assert 0.90 <= test_prob_extreme <= 1.0, f"Extreme anomaly probability not near 1.0: {test_prob_extreme}"
    print(f"  Probability Normalization: Verified (P(0)={test_prob_min:.3f}, P(Threshold)={test_prob_thresh:.3f}, P(Extreme)={test_prob_extreme:.3f})")

    # Save calibration manifest
    calibration = {
        'threshold_evt': float(evt_ensemble['threshold']),
        'threshold_p99': float(p99_ensemble),
        'threshold_recon_evt': float(evt_recon['threshold']),
        'threshold_recon_p99': float(p99_recon),
        'threshold_mahalanobis_p99': float(p99_mahalanobis),
        'evt_shape': float(evt_ensemble['shape']),
        'evt_scale': float(evt_ensemble['scale']),
        'evt_init_threshold': float(evt_ensemble['init_threshold']),
        'steepness': 0.5,
        'steepness_k': 2.0,
        'target_fpr': 0.01,
        'actual_fpr': actual_fpr,
        'fpr_verified': True,
        'normalization_guard_passed': True,
        'model': 'sequence_vae_geometry_novel',
        'val_samples': len(val_sequences),
        'mean_recon_error': float(np.mean(val_errors)) if val_errors else 0.0,
        'std_recon_error': float(np.std(val_errors)) if val_errors else 0.0,
        'mean_mahalanobis': float(np.mean(val_mahalanobis)) if val_mahalanobis else 0.0,
        'std_mahalanobis': float(np.std(val_mahalanobis)) if val_mahalanobis else 0.0,
    }

    calib_path = Path('artifacts/calibration/vae_calibration.json')
    calib_path.parent.mkdir(parents=True, exist_ok=True)

    with open(calib_path, 'w', encoding='utf-8') as f:
        json.dump(calibration, f, indent=2)

    # Mirror calibration to legacy path
    legacy_calib = Path('artifacts/calibration/sequence_vae_calibration.json')
    with open(legacy_calib, 'w', encoding='utf-8') as f:
        json.dump({
            "method": "evt_peaks_over_threshold",
            "threshold_evt": float(evt_ensemble['threshold']),
            "threshold_p99": float(p99_ensemble),
            "steepness_k": 0.5,
            "percentile": 99.0,
            "is_fitted": True,
            "model": "sequence_vae_geometry_novel"
        }, f, indent=2)

    # Save training history
    history_path = Path(args.save_path).parent / 'training_history.json'
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(training_history, f, indent=2)

    # Save latent distribution
    latent_dist_path = Path(args.save_path).parent / 'latent_distribution.npz'
    np.savez(
        latent_dist_path,
        mean=model.latent_mean,
        cov_inv=model.latent_cov_inv,
    )

    # Mirror checkpoints to canonical & legacy locations for seamless inference
    canonical_pt = Path('artifacts/checkpoints/geometry/sequence_vae.pt')
    canonical_pt.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), canonical_pt)

    weights_mirror = Path('ml/models/geometry/weights/sequence_vae.pt')
    weights_mirror.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), weights_mirror)

    print(f"\n" + "=" * 70)
    print("Enhanced Sequence VAE Training Complete!")
    print("=" * 70)
    print(f"Model saved to:     {args.save_path}")
    print(f"Mirrored to:        {canonical_pt}")
    print(f"                    {weights_mirror}")
    print(f"Calibration saved:  {calib_path}")
    print(f"Training history:   {history_path}")
    print(f"\nCalibration parameters:")
    print(f"  P99 reconstruction error: {p99_recon:.4f}")
    print(f"  P99 Mahalanobis distance: {p99_mahalanobis:.4f}")
    print(f"  P99 ensemble score: {p99_ensemble:.4f}")
    print(f"  Target FPR: 1%")

    return model, calibration


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Enhanced Sequence VAE")

    # Training parameters
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--beta', type=float, default=0.01, help='Beta-VAE weight for KL divergence')
    parser.add_argument('--batch-size', '--batch_size', dest='batch_size', type=int, default=64, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--weight-decay', '--weight_decay', dest='weight_decay', type=float, default=1e-4, help='Weight decay')
    parser.add_argument('--grad-clip', '--grad_clip', dest='grad_clip', type=float, default=1.0, help='Gradient clipping norm')
    parser.add_argument('--patience', type=int, default=8, help='Early stopping patience')

    # Model parameters - ACCEPT BOTH HYPHEN AND UNDERSCORE FORMATS
    parser.add_argument('--latent-dim', '--latent_dim', dest='latent_dim', type=int, default=16,
                        help='Latent space dimension')
    parser.add_argument('--seq-len', '--seq_len', dest='seq_len', type=int, default=80,
                        help='Sequence length')
    parser.add_argument('--n-features', '--n_features', dest='n_features', type=int, default=5,
                        help='Number of input features')

    # KL annealing
    parser.add_argument('--kl-annealing', '--kl_annealing', dest='kl_annealing', action='store_true', default=True,
                        help='Use KL annealing')
    parser.add_argument('--no-kl-annealing', '--no_kl_annealing', dest='kl_annealing', action='store_false')
    parser.add_argument('--annealing-epochs', '--annealing_epochs', dest='annealing_epochs', type=int, default=10,
                        help='Number of epochs for KL annealing')

    # Paths
    parser.add_argument('--save-path', '--save_path', dest='save_path', type=str,
                        default='artifacts/checkpoints/geometry/sequence_vae_enhanced.pt')
    parser.add_argument('--data-path', '--data_path', dest='data_path', type=str,
                        default='data/processed/normal_sequences/')

    args = parser.parse_args()

    train_enhanced_vae(args)
