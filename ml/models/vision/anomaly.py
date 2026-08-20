# PatchCore unsupervised visual anomaly detector for novel surface defects (tc.v1 SOTA).

import os
from pathlib import Path
from typing import List, Tuple, Optional, Union, Dict, Any
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

try:
    import torchvision.models as models
    from torchvision import transforms
except ImportError:
    models = None
    transforms = None

try:
    import faiss
except ImportError:
    faiss = None

try:
    import cv2
except ImportError:
    cv2 = None

from ml.core.schema import DefectClass, CalibratedSignal, SignalType
from ml.core.registry import register_model, ModelRegistry
from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator


def get_default_transform(img_size: int = 224):
    """Default PyTorch image normalization transform for ResNet/WideResNet backbones."""
    if transforms is None:
        return None
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


@register_model("patchcore_anomaly_detector")
class PatchCoreAnomalyDetector:
    """
    PatchCore anomaly detector for novel/unseen visual defects.
    Extracts multi-scale patch features, computes distance against a normal memory bank,
    and converts distance into calibrated probability and localized bounding boxes.
    """

    def __init__(
        self,
        backbone_name: str = "wide_resnet50_2",
        fallback_backbone: str = "resnet18",
        device: str = "cpu",
        patch_size: int = 3,
        k_nearest: int = 1,
        sigma: float = 4.0,
        confidence_threshold: float = 0.50,
        checkpoint_path: Optional[Union[str, Path]] = None,
        calibration_path: Optional[Union[str, Path]] = None,
    ):
        self.backbone_name = backbone_name
        self.fallback_backbone = fallback_backbone
        self.device = torch.device(device if torch.cuda.is_available() and device != "cpu" else "cpu")
        self.patch_size = patch_size
        self.k_nearest = k_nearest
        self.sigma = sigma
        self.threshold = confidence_threshold

        self.backbone: Optional[nn.Module] = None
        self.feature_dim: int = 1536 if "wide" in backbone_name else 384
        self.memory_bank: Optional[np.ndarray] = None
        self.faiss_index: Any = None
        self.nn_model: Any = None
        self.calibrator = SigmoidDistanceCalibrator()
        self.transform = get_default_transform(224)

        # Initialize neural backbone
        self._init_backbone()

        # Resolve weights and calibration if not explicitly given
        if checkpoint_path is None:
            default_ckpt = ModelRegistry.get_trained_weights("vision", "patchcore_memory_bank.npz")
            if default_ckpt.exists():
                checkpoint_path = default_ckpt

        if calibration_path is None:
            default_cal = ModelRegistry.get_calibration_path("patchcore")
            if default_cal.exists():
                calibration_path = default_cal

        if checkpoint_path and os.path.exists(checkpoint_path):
            self.load_memory_bank(checkpoint_path)

        if calibration_path and os.path.exists(calibration_path):
            self.calibrator = SigmoidDistanceCalibrator.load(calibration_path)

    def _init_backbone(self):
        """Load frozen pretrained feature extractor (eval mode)."""
        if models is None:
            return

        try:
            if self.backbone_name == "wide_resnet50_2":
                weights = models.Wide_ResNet50_2_Weights.DEFAULT
                base = models.wide_resnet50_2(weights=weights)
                self.feature_dim = 1536
            else:
                weights = models.ResNet18_Weights.DEFAULT
                base = models.resnet18(weights=weights)
                self.feature_dim = 384
        except Exception:
            # Fallback to lighter resnet18 if wide_resnet download fails
            weights = models.ResNet18_Weights.DEFAULT
            base = models.resnet18(weights=weights)
            self.feature_dim = 384

        # Freeze all layers
        for param in base.parameters():
            param.requires_grad = False
        base.eval()
        self.backbone = base.to(self.device)

    def extract_features(self, x: torch.Tensor) -> Tuple[torch.Tensor, Tuple[int, int]]:
        """
        Extract multi-scale patch features from layer2 and layer3.
        Returns flattened patch feature tensor (N_patches, Feature_Dim) and (H_feature, W_feature).
        """
        if self.backbone is None:
            raise RuntimeError("Backbone is not initialized.")

        # Forward pass through initial layers
        x = self.backbone.conv1(x)
        x = self.backbone.bn1(x)
        x = self.backbone.relu(x)
        x = self.backbone.maxpool(x)

        x = self.backbone.layer1(x)
        l2 = self.backbone.layer2(x)
        l3 = self.backbone.layer3(l2)

        # Patch neighborhood pooling (aggregates local textures)
        pool = nn.AvgPool2d(kernel_size=self.patch_size, stride=1, padding=self.patch_size // 2)
        p2 = pool(l2)
        p3 = pool(l3)

        # Resize layer3 to match layer2 spatial resolution
        target_size = p2.shape[-2:]
        p3_resized = F.interpolate(p3, size=target_size, mode="bilinear", align_corners=False)

        # Concatenate along channel dimension
        features = torch.cat([p2, p3_resized], dim=1)  # (B, C2+C3, H, W)
        b, c, h, w = features.shape
        self.feature_dim = c

        # Permute and reshape to (B * H * W, C)
        features = features.permute(0, 2, 3, 1).contiguous().view(-1, c)
        return features, (h, w)

    def set_memory_bank(self, memory_bank: np.ndarray):
        """Set the memory bank array and build the nearest-neighbor search index."""
        self.memory_bank = np.ascontiguousarray(memory_bank, dtype=np.float32)
        dim = self.memory_bank.shape[1]
        self.feature_dim = dim

        if faiss is not None:
            index = faiss.IndexFlatL2(dim)
            index.add(self.memory_bank)
            self.faiss_index = index
        else:
            from sklearn.neighbors import NearestNeighbors
            nn_model = NearestNeighbors(n_neighbors=self.k_nearest, metric="euclidean", algorithm="auto")
            nn_model.fit(self.memory_bank)
            self.nn_model = nn_model

    def save_memory_bank(self, filepath: Union[str, Path]):
        """Save the memory bank array to .npz file."""
        if self.memory_bank is None:
            raise ValueError("No memory bank to save.")
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(p, memory_bank=self.memory_bank)

    def load_memory_bank(self, filepath: Union[str, Path]):
        """Load memory bank from .npz file and build index."""
        p = Path(filepath)
        if not p.exists():
            return
        data = np.load(p)
        if "memory_bank" in data:
            bank = data["memory_bank"]
            # Validate feature dimension strictly against backbone
            if bank.shape[1] == self.feature_dim:
                self.set_memory_bank(bank)

    def predict_raw(self, image: Union[np.ndarray, Image.Image]) -> Tuple[float, np.ndarray]:
        """
        Run PatchCore inference on a single image.
        Returns:
            max_distance: float (raw nearest-neighbor L2 distance)
            anomaly_map: 2D numpy array (H, W) smoothed anomaly heatmap
        """
        if self.memory_bank is None:
            return 0.0, np.zeros((224, 224), dtype=np.float32)

        # Prepare tensor
        if isinstance(image, np.ndarray):
            if image.ndim == 2:
                pil_img = Image.fromarray(image).convert("RGB")
            elif image.shape[2] == 3:
                pil_img = Image.fromarray(image)
            else:
                pil_img = Image.fromarray(image[:, :, :3])
        else:
            pil_img = image.convert("RGB")

        orig_w, orig_h = pil_img.size
        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            patch_features, (fh, fw) = self.extract_features(tensor)
            feat_np = patch_features.cpu().numpy().astype(np.float32)

            if feat_np.shape[1] != self.memory_bank.shape[1]:
                return 0.0, np.zeros((orig_h, orig_w), dtype=np.float32)

            # Query nearest neighbor in memory bank
            if self.faiss_index is not None:
                distances, _ = self.faiss_index.search(feat_np, self.k_nearest)
                patch_scores = np.sqrt(np.maximum(0.0, distances[:, 0]))  # L2 distance
            elif self.nn_model is not None:
                distances, _ = self.nn_model.kneighbors(feat_np, n_neighbors=self.k_nearest)
                patch_scores = distances[:, 0]
            else:
                # Direct vector distance fallback
                diff = feat_np[:, None, :] - self.memory_bank[None, :, :]
                dists = np.linalg.norm(diff, axis=-1)
                patch_scores = np.min(dists, axis=-1)

        max_distance = float(np.max(patch_scores))

        # Reshape to spatial feature grid and interpolate to original size
        score_map = patch_scores.reshape(fh, fw)

        # Gaussian smoothing
        if cv2 is not None:
            smoothed = cv2.GaussianBlur(score_map, (0, 0), sigmaX=self.sigma, sigmaY=self.sigma)
            resized_map = cv2.resize(smoothed, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        else:
            from scipy.ndimage import gaussian_filter, zoom
            smoothed = gaussian_filter(score_map, sigma=self.sigma)
            zoom_h = orig_h / fh
            zoom_w = orig_w / fw
            resized_map = zoom(smoothed, (zoom_h, zoom_w), order=1)

        return max_distance, resized_map

    def extract_bounding_box(self, anomaly_map: np.ndarray, threshold: float = 0.50) -> Optional[Tuple[float, float, float, float]]:
        """
        Extract bounding box around the most anomalous region in the heatmap.
        Returns (x1, y1, x2, y2) in pixel coordinates or None.
        """
        h, w = anomaly_map.shape[:2]
        denom = (anomaly_map.max() - anomaly_map.min() + 1e-8)
        norm_map = (anomaly_map - anomaly_map.min()) / denom
        mask = (norm_map > threshold).astype(np.uint8)

        if cv2 is not None:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                max_idx = np.unravel_index(np.argmax(anomaly_map), anomaly_map.shape)
                cy, cx = max_idx[0], max_idx[1]
                half = min(h, w) * 0.1
                return (max(0.0, cx - half), max(0.0, cy - half), min(float(w), cx + half), min(float(h), cy + half))

            largest = max(contours, key=cv2.contourArea)
            x, y, bw, bh = cv2.boundingRect(largest)
            return (float(x), float(y), float(x + bw), float(y + bh))
        else:
            y_indices, x_indices = np.where(mask > 0)
            if len(x_indices) == 0:
                return None
            return (float(x_indices.min()), float(y_indices.min()), float(x_indices.max()), float(y_indices.max()))

    def predict(self, frame: np.ndarray) -> List[CalibratedSignal]:
        """
        Run PatchCore inference and return contract-compliant CalibratedSignal.
        Frame should be a HxWxC uint8 NumPy array.
        """
        if self.memory_bank is None:
            return []

        h, w = frame.shape[:2]
        raw_distance, anomaly_map = self.predict_raw(frame)

        # Calibrate raw distance into [0.0, 1.0] probability
        calibrated_score = self.calibrator.scale(raw_distance)
        fired = bool(calibrated_score >= self.threshold)

        bbox = None
        if fired:
            bbox = self.extract_bounding_box(anomaly_map, threshold=0.45)

        signal = CalibratedSignal(
            stream_name="patchcore_anomaly",
            raw_score=raw_distance,
            calibrated_prob=calibrated_score,
            predicted_class=DefectClass.VISUAL_ANOMALY,
            is_anomaly=fired,
            signal_type=SignalType.VISUAL_NOVEL,
            threshold=self.threshold,
            bbox=bbox,
            explanation=f"PatchCore detected novel visual anomaly with score {calibrated_score:.1%} (raw L2: {raw_distance:.2f})",
            metadata={
                "raw_distance": raw_distance,
                "calibrated_score": calibrated_score,
                "image_width": w,
                "image_height": h,
            },
        )

        return [signal]
