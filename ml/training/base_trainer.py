# Shared training loop: checkpointing, logging, early stopping.

import os
from typing import Optional, Callable
import torch
import torch.nn as nn
from torch.utils.data import DataLoader


class BaseTrainer:
    """Standard PyTorch training scaffold with checkpointing and early stopping."""

    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        criterion: nn.Module,
        device: str = "cpu",
        checkpoint_dir: str = "artifacts/checkpoints",
        patience: int = 5,
    ):
        self.model = model.to(device)
        self.optimizer = optimizer
        self.criterion = criterion
        self.device = device
        self.checkpoint_dir = checkpoint_dir
        self.patience = patience
        os.makedirs(checkpoint_dir, exist_ok=True)

    def train_epoch(self, dataloader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        for x, y in dataloader:
            x, y = x.to(self.device), y.to(self.device)
            self.optimizer.zero_grad()
            out = self.model(x)
            loss = self.criterion(out, y)
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item()
        return total_loss / max(1, len(dataloader))

    def evaluate(self, dataloader: DataLoader) -> float:
        self.model.eval()
        total_loss = 0.0
        with torch.no_grad():
            for x, y in dataloader:
                x, y = x.to(self.device), y.to(self.device)
                out = self.model(x)
                loss = self.criterion(out, y)
                total_loss += loss.item()
        return total_loss / max(1, len(dataloader))

    def save_checkpoint(self, filename: str):
        path = os.path.join(self.checkpoint_dir, filename)
        torch.save(self.model.state_dict(), path)
