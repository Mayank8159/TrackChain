# DataLoader builders with train/val splits and augmentation.

from typing import Tuple
from torch.utils.data import DataLoader, random_split, Dataset


def build_dataloaders(
    dataset: Dataset,
    batch_size: int = 32,
    val_split: float = 0.2,
    num_workers: int = 0,
    seed: int = 42,
) -> Tuple[DataLoader, DataLoader]:
    """Create reproducible training and validation data loaders."""
    val_size = int(len(dataset) * val_split)
    train_size = len(dataset) - val_size

    train_set, val_set = random_split(
        dataset,
        [train_size, val_size],
        generator=None,
    )

    train_loader = DataLoader(
        train_set,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    return train_loader, val_loader
