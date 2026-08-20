# PyTorch Datasets for RSDDs, NEU, and fastener imagery.

import os
from typing import Callable, List, Optional, Tuple
import numpy as np
import torch
from torch.utils.data import Dataset


class RailSurfaceDefectDataset(Dataset):
    """PyTorch dataset for RSDDs and NEU rail surface defect images."""

    def __init__(
        self,
        image_paths: List[str],
        labels: Optional[List[int]] = None,
        transform: Optional[Callable] = None,
        is_normal_only: bool = False,
    ):
        self.image_paths = image_paths
        self.labels = labels if labels is not None else [0] * len(image_paths)
        self.transform = transform
        self.is_normal_only = is_normal_only

        if self.is_normal_only and labels is not None:
            normal_indices = [i for i, l in enumerate(labels) if l == 0]
            self.image_paths = [self.image_paths[i] for i in normal_indices]
            self.labels = [0] * len(self.image_paths)

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        path = self.image_paths[idx]
        # Generate dummy array if file doesn't exist on disk yet
        if os.path.exists(path):
            import cv2
            img = cv2.imread(path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            img = np.zeros((224, 224, 3), dtype=np.uint8)

        if self.transform:
            img_tensor = self.transform(img)
        else:
            img_tensor = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0

        return img_tensor, self.labels[idx]


class GeometrySequenceDataset(Dataset):
    """PyTorch dataset for EN 13848 multi-channel geometry sequence windows."""

    def __init__(
        self,
        features: np.ndarray,  # shape: [N, window_len, num_channels]
        labels: np.ndarray,    # shape: [N]
    ):
        self.features = torch.from_numpy(features).float()
        self.labels = torch.from_numpy(labels).long()

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]
