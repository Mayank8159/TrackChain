"""
ml/training/train_sequence_vae.py
Train the 1D-CNN Sequence VAE on normal track geometry sequences (tc.v1 SOTA).
"""

from ml.scripts.train_sequence_vae import train_sequence_vae

__all__ = ["train_sequence_vae"]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train 1D-CNN Sequence VAE for Novel Geometry.")
    parser.add_argument("--epochs", type=int, default=25, help="Number of training epochs")
    parser.add_argument("--beta", type=float, default=0.01, help="Beta-VAE KL weight")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--save-path", default="artifacts/checkpoints/geometry/sequence_vae.pt")
    args = parser.parse_args()

    train_sequence_vae(
        epochs=args.epochs,
        beta=args.beta,
        batch_size=args.batch_size,
        lr=args.lr,
        save_path=args.save_path,
    )
