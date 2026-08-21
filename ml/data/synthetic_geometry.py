"""
ml/data/synthetic_geometry.py
Generates EN 13848-compliant synthetic geometry sequences for Bi-LSTM training and evaluation.
"""

from typing import Dict, Tuple, List, Optional, Union, Any
from enum import IntEnum
import numpy as np
from scipy.ndimage import gaussian_filter1d
import torch
from torch.utils.data import Dataset, DataLoader

from ml.core.schema import DefectClass


class GeometryFaultType(IntEnum):
    NORMAL = 0
    DIPPED_JOINT = 1
    CYCLIC_TOP = 2
    TWIST_FAULT = 3
    ALIGNMENT_KINK = 4
    BUCKLING_RISK = 5


CLASS_MAP = {
    0: "NORMAL",
    1: "DIPPED_JOINT",
    2: "CYCLIC_TOP",
    3: "TWIST_FAULT",
    4: "ALIGNMENT_KINK",
    5: "BUCKLING_RISK",
}

CLASS_TO_DEFECT_ENUM = {
    0: DefectClass.NORMAL,
    1: DefectClass.DIPPED_JOINT,
    2: DefectClass.CYCLIC_TOP,
    3: DefectClass.TWIST_FAULT,
    4: DefectClass.ALIGNMENT_KINK,
    5: DefectClass.BUCKLING_RISK,
}

DEFECT_ENUM_TO_CLASS = {v: k for k, v in CLASS_TO_DEFECT_ENUM.items()}


class SyntheticGeometryDataset(Dataset):
    """
    Parametric synthetic dataset generating 5-channel EN 13848 track geometry sequences
    (0: Twist_3m, 1: Versine_10m, 2: Versine_20m, 3: Unevenness_10m, 4: Cant).
    """

    def __init__(
        self,
        num_samples: int = 2000,
        seq_len: int = 80,
        bin_size: float = 0.25,
        noise_std: float = 0.5,
        num_classes: int = 5,
        random_seed: Optional[int] = None,
    ):
        self.num_samples = num_samples
        self.seq_len = seq_len
        self.bin_size = bin_size
        self.noise_std = noise_std
        self.num_classes = num_classes
        self.rng = np.random.RandomState(random_seed)
        self.data, self.labels = self._generate_dataset()

    def _generate_psd_noise(self, length: int) -> np.ndarray:
        """Generates 1D track noise based on EN 13848-2 PSD decay."""
        freqs = np.fft.rfftfreq(length, d=self.bin_size)
        freqs[0] = 1e-6
        psd = 0.005 / (freqs**2 + 0.001)
        phase = self.rng.uniform(0, 2 * np.pi, len(freqs))
        profile = np.fft.irfft(np.sqrt(psd) * np.exp(1j * phase), n=length)
        return profile * 100.0 * self.noise_std  # Scaled to physical mm

    def _generate_dataset(self) -> Tuple[torch.Tensor, torch.Tensor]:
        X = np.zeros((self.num_samples, self.seq_len, 5), dtype=np.float32)
        y = np.zeros(self.num_samples, dtype=np.int64)

        # Features: 0:Twist, 1:Versine10m, 2:Versine20m, 3:Unevenness, 4:Cant
        for i in range(self.num_samples):
            # Base noise for all 5 channels
            base_noise = np.column_stack([self._generate_psd_noise(self.seq_len) for _ in range(5)])
            X[i] = base_noise

            # Assign class (balanced distribution)
            fault_type = i % self.num_classes
            y[i] = fault_type

            if fault_type == GeometryFaultType.NORMAL:
                continue  # Just baseline PSD track noise

            # Inject parametric fault shape at a random location in the window
            center = int(self.rng.randint(20, self.seq_len - 20))

            if fault_type == GeometryFaultType.DIPPED_JOINT:
                # Gaussian dip in Unevenness (Channel 3)
                x_vals = np.arange(self.seq_len, dtype=np.float32)
                dip = -8.0 * np.exp(-0.5 * ((x_vals - center) / 2.0) ** 2)
                X[i, :, 3] += dip

            elif fault_type == GeometryFaultType.CYCLIC_TOP:
                # Sine wave in Unevenness (Channel 3)
                x_vals = np.arange(self.seq_len, dtype=np.float32) * self.bin_size
                wave = 5.0 * np.sin(2 * np.pi * x_vals / 6.0)  # 5mm amp, 6m wavelength
                window = np.exp(-0.5 * ((x_vals - center * self.bin_size) / 4.0) ** 2)
                X[i, :, 3] += wave * window

            elif fault_type == GeometryFaultType.TWIST_FAULT:
                # Tanh step in Cant (Channel 4) and Twist (Channel 0)
                x_vals = np.arange(self.seq_len, dtype=np.float32)
                ramp = 4.0 * np.tanh((x_vals - center) / 1.5)
                X[i, :, 4] += ramp
                # Twist is spatial derivative of cant over 3m base
                X[i, :, 0] += np.gradient(ramp, self.bin_size) * 3.0

            elif fault_type == GeometryFaultType.ALIGNMENT_KINK:
                # Step function in Versine (Channels 1 & 2)
                x_vals = np.arange(self.seq_len, dtype=np.float32)
                kink = 6.0 * np.tanh((x_vals - center) / 0.5)
                X[i, :, 1] += kink
                X[i, :, 2] += kink * 0.8  # 20m chord sees it slightly smoothed

            elif fault_type == GeometryFaultType.BUCKLING_RISK:
                # Broad lateral bow in Versine (Channels 1 & 2)
                x_vals = np.arange(self.seq_len, dtype=np.float32)
                bow = 10.0 * np.exp(-0.5 * ((x_vals - center) / 8.0) ** 2)
                X[i, :, 1] += bow
                X[i, :, 2] += bow * 1.2

        return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.long)

    def __len__(self) -> int:
        return self.num_samples

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.data[idx], self.labels[idx]


class ParametricGeometryGenerator:
    """Convenience generator for single parametric geometry windows with metadata."""

    def __init__(
        self,
        window_length_m: float = 20.0,
        step_m: float = 0.25,
        random_seed: Optional[int] = None,
    ):
        self.window_length_m = window_length_m
        self.step_m = step_m
        self.seq_len = int(round(window_length_m / step_m))
        self.rng = np.random.RandomState(random_seed)

    def generate_window(
        self,
        defect_class: Union[int, DefectClass] = 0,
        spatial_shift_m: Optional[float] = None,
        amplitude_scale: float = 1.0,
        noise_level_mm: float = 0.5,
    ) -> Tuple[np.ndarray, int, Dict[str, Any]]:
        if isinstance(defect_class, DefectClass):
            cid = DEFECT_ENUM_TO_CLASS.get(defect_class, 0)
        else:
            cid = int(defect_class)

        center_bin = int(round(spatial_shift_m / self.step_m)) if spatial_shift_m is not None else int(self.rng.randint(20, self.seq_len - 20))
        center_bin = int(np.clip(center_bin, 10, self.seq_len - 10))

        ds = SyntheticGeometryDataset(
            num_samples=max(6, cid + 1),
            seq_len=self.seq_len,
            bin_size=self.step_m,
            noise_std=noise_level_mm,
            num_classes=6,
            random_seed=int(self.rng.randint(0, 100000)),
        )
        
        # Inject exact requested class
        feat, _ = ds[cid]
        feat_np = feat.numpy().copy()

        metadata = {
            "class_id": cid,
            "class_name": CLASS_MAP.get(cid, "UNKNOWN"),
            "defect_center_bin": center_bin,
            "defect_center_m": float(center_bin * self.step_m),
            "amplitude_mm": float(amplitude_scale),
        }
        return feat_np, cid, metadata


def create_synthetic_data_loaders(
    train_samples_per_class: int = 250,
    val_samples_per_class: int = 50,
    batch_size: int = 32,
    num_classes: int = 5,
    random_seed: int = 42,
) -> Tuple[DataLoader, DataLoader]:
    """Factory creating Train and Validation DataLoaders."""
    train_dataset = SyntheticGeometryDataset(
        num_samples=train_samples_per_class * num_classes,
        num_classes=num_classes,
        random_seed=random_seed,
    )
    val_dataset = SyntheticGeometryDataset(
        num_samples=val_samples_per_class * num_classes,
        num_classes=num_classes,
        random_seed=random_seed + 999,
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader
