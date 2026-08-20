# Temperature/Platt scaling to turn network logits into true probabilities.

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np


class TemperatureScaler(nn.Module):
    """Post-processing calibration module that learns a single temperature parameter T to calibrate logits."""

    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        temperature = self.temperature.unsqueeze(1).expand(logits.size(0), logits.size(1))
        return logits / temperature

    def fit(self, val_logits: np.ndarray, val_labels: np.ndarray, lr: float = 0.01, max_iter: int = 50):
        """Fit optimal temperature using NLL loss on validation set."""
        logits_t = torch.from_numpy(val_logits).float()
        labels_t = torch.from_numpy(val_labels).long()

        nll_criterion = nn.CrossEntropyLoss()
        optimizer = optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)

        def eval_step():
            optimizer.zero_grad()
            loss = nll_criterion(self.forward(logits_t), labels_t)
            loss.backward()
            return loss

        optimizer.step(eval_step)
        return float(self.temperature.item())

    def calibrate_probs(self, logits: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            scaled = self.forward(torch.from_numpy(logits).float())
            probs = torch.softmax(scaled, dim=1).numpy()
        return probs
