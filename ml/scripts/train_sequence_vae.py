"""
ml/scripts/train_sequence_vae.py
Trains the 1D-CNN Sequence VAE on normal track geometry sequences (Beta-VAE, beta=0.01).
"""

import os
import sys
import argparse
from pathlib import Path
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ml.models.geometry.sequence_vae import SequenceVAE, SequenceVAEDetector
from ml.data.synthetic_geometry import SyntheticGeometryDataset, GeometryFaultType
from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator


def train_sequence_vae(
    num_normal_samples: int = 3000,
    val_samples: int = 600,
    seq_len: int = 80,
    n_features: int = 5,
    latent_dim: int = 16,
    beta: float = 0.01,
    epochs: int = 25,
    batch_size: int = 64,
    lr: float = 1e-3,
    save_path: str = "artifacts/checkpoints/geometry/sequence_vae.pt",
    calibrator_save_path: str = "artifacts/calibration/sequence_vae_calibration.json",
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[VAE] Training 1D-CNN Sequence VAE on device: {device}")

    # 1. Generate Normal Track Geometry Dataset
    print(f"[VAE] Synthesizing {num_normal_samples} nominal EN 13848 track sequences...")
    full_train_ds = SyntheticGeometryDataset(
        num_samples=num_normal_samples * 2,
        seq_len=seq_len,
        num_classes=5,
        random_seed=42,
    )
    # Filter ONLY normal sequences (label == 0)
    normal_train_mask = (full_train_ds.labels == GeometryFaultType.NORMAL)
    normal_train_data = full_train_ds.data[normal_train_mask][:num_normal_samples]

    full_val_ds = SyntheticGeometryDataset(
        num_samples=val_samples * 2,
        seq_len=seq_len,
        num_classes=5,
        random_seed=999,
    )
    normal_val_mask = (full_val_ds.labels == GeometryFaultType.NORMAL)
    normal_val_data = full_val_ds.data[normal_val_mask][:val_samples]

    train_loader = DataLoader(
        TensorDataset(normal_train_data),
        batch_size=batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(normal_val_data),
        batch_size=batch_size,
        shuffle=False,
    )

    # 2. Instantiate 1D-CNN Model
    model = SequenceVAE(
        seq_len=seq_len,
        n_features=n_features,
        latent_dim=latent_dim,
    ).to(device)

    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    # 3. Training Loop
    print(f"[VAE] Starting optimization ({epochs} epochs, Beta={beta})...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        recon_total = 0.0
        kld_total = 0.0
        n_batches = 0

        for (batch_x,) in train_loader:
            batch_x = batch_x.to(device)
            optimizer.zero_grad()

            recon_x, mu, logvar = model(batch_x)
            loss, recon_loss, kld_loss = model.loss_function(
                recon_x, batch_x, mu, logvar, beta=beta
            )

            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            recon_total += recon_loss.item()
            kld_total += kld_loss.item()
            n_batches += 1

        scheduler.step()

        if (epoch + 1) % 5 == 0 or epoch == 0 or epoch == epochs - 1:
            # Validation reconstruction error
            model.eval()
            val_mse = 0.0
            val_batches = 0
            with torch.no_grad():
                for (batch_val,) in val_loader:
                    batch_val = batch_val.to(device)
                    recon_val, _, _ = model(batch_val)
                    val_mse += torch.mean((recon_val - batch_val) ** 2).item()
                    val_batches += 1

            avg_val_mse = val_mse / max(1, val_batches)
            print(
                f"  Epoch [{epoch+1:02d}/{epochs:02d}] "
                f"Train Loss: {total_loss/n_batches:.4f} (Recon: {recon_total/n_batches:.4f}, KLD: {kld_total/n_batches:.4f}) | "
                f"Val MSE: {avg_val_mse:.4f}"
            )

    # 4. Fit Sigmoid Distance Calibrator on Normal Validation Errors
    print("[VAE] Fitting Sigmoid calibrator on normal validation reconstruction errors...")
    model.eval()
    val_errors = []
    with torch.no_grad():
        for (batch_val,) in val_loader:
            batch_val = batch_val.to(device)
            errs = model.compute_anomaly_score(batch_val).cpu().numpy()
            val_errors.extend(errs.tolist())

    calibrator = SigmoidDistanceCalibrator(steepness_k=2.5, percentile=99.0)
    p99_thresh = calibrator.fit(val_errors)
    print(f"      Fitted P99 Anomaly Threshold: {p99_thresh:.4f}")

    # 5. Save Checkpoint & Calibrator
    out_dir = os.path.dirname(save_path)
    os.makedirs(out_dir, exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"[OK] Sequence VAE weights saved to: {save_path}")

    # Mirror to ml/models/geometry/weights/
    mirror_path = "ml/models/geometry/weights/sequence_vae.pt"
    os.makedirs(os.path.dirname(mirror_path), exist_ok=True)
    torch.save(model.state_dict(), mirror_path)

    calibrator.save(calibrator_save_path)
    print(f"[OK] Sigmoid calibrator state saved to: {calibrator_save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train 1D-CNN Sequence VAE for Novel Geometry.")
    parser.add_argument("--epochs", type=int, default=25, help="Number of training epochs")
    parser.add_argument("--beta", type=float, default=0.01, help="Beta-VAE KL weight")
    parser.add_argument("--batch-size", "--batch_size", dest="batch_size", type=int, default=64, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--latent-dim", "--latent_dim", dest="latent_dim", type=int, default=16, help="Latent space dimension")
    parser.add_argument("--seq-len", "--seq_len", dest="seq_len", type=int, default=80, help="Sequence length")
    parser.add_argument("--n-features", "--n_features", dest="n_features", type=int, default=5, help="Number of input features")
    parser.add_argument("--save-path", "--save_path", dest="save_path", default="artifacts/checkpoints/geometry/sequence_vae.pt")
    args = parser.parse_args()

    train_sequence_vae(
        epochs=args.epochs,
        beta=args.beta,
        batch_size=args.batch_size,
        lr=args.lr,
        latent_dim=args.latent_dim,
        seq_len=args.seq_len,
        n_features=args.n_features,
        save_path=args.save_path,
    )
