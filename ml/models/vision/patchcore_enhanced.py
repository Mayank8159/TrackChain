"""
Enhanced PatchCore implementation with:
- Multi-scale feature extraction (layer2 + layer3 with adaptive pooling)
- Adaptive patch sizes (e.g. 3x3, 5x5, 7x7)
- Greedy Minimax / k-center coreset sampling
- SparseRandomProjection dimension reduction
- Ensemble FAISS memory banks
- Statistical P99 + Nelder-Mead sigmoid probability calibration
- Anomaly heatmap generation & bounding box localization
- Full contract compliance with TrackChain CalibratedSignal schema
"""
import os
import sys
import json
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union, Any
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms

try:
    import faiss
except ImportError:
    faiss = None

try:
    import cv2
except ImportError:
    cv2 = None

from sklearn.random_projection import SparseRandomProjection
from scipy.special import expit
from scipy.optimize import minimize
from tqdm import tqdm

from ml.core.schema import DefectClass, CalibratedSignal, SignalType
from ml.core.registry import register_model, ModelRegistry


def get_default_transform(img_size: int = 224):
    """Image normalization transform for ResNet/WideResNet backbones."""
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


class ImageDataset(torch.utils.data.Dataset):
    """Image dataset loader for PatchCore memory bank extraction."""
    
    def __init__(self, image_paths: List[Path], transform=None):
        self.image_paths = [Path(p) for p in image_paths]
        self.transform = transform or get_default_transform(224)
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        try:
            pil_img = Image.open(img_path).convert("RGB")
            return self.transform(pil_img)
        except Exception:
            # Fallback zero tensor
            return torch.zeros((3, 224, 224), dtype=torch.float32)


@register_model("enhanced_patchcore")
class EnhancedPatchCore:
    """
    Enhanced PatchCore anomaly detector with multi-scale feature extraction,
    ensemble memory banks, FAISS indexing, and calibrated probability scaling.
    """
    
    def __init__(
        self,
        backbone: str = "wide_resnet50_2",
        layers: Optional[List[str]] = None,
        patch_sizes: Optional[List[int]] = None,
        coreset_ratio: float = 0.08,
        dimension_reduction: bool = True,
        target_dim: int = 128,
        device: str = "auto",
        patch_weights: Optional[Dict[str, float]] = None,
        sigma: float = 4.0,
        threshold: float = 0.50,
    ):
        self.backbone_name = backbone
        self.layers = layers or ["layer2", "layer3"]
        self.patch_sizes = patch_sizes or [3, 5, 7]
        self.coreset_ratio = coreset_ratio
        self.dimension_reduction = dimension_reduction
        self.target_dim = target_dim
        self.sigma = sigma
        self.threshold = threshold
        
        # Default patch ensemble weights
        if patch_weights:
            self.patch_weights = patch_weights
        else:
            n_scales = len(self.patch_sizes)
            self.patch_weights = {f"patch_{ps}": 1.0 / n_scales for ps in self.patch_sizes}
        
        # Device resolution
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device if torch.cuda.is_available() and device != "cpu" else "cpu")
        
        # Hooks and memory banks
        self.features: Dict[str, torch.Tensor] = {}
        self.hooks = []
        self.backbone: Optional[nn.Module] = None
        self.feature_dim = 1536 if "wide" in backbone else (512 if backbone == "resnet50" else 384)
        
        self.memory_banks: Dict[int, Dict[str, Any]] = {}
        self.projectors: Dict[int, Any] = {}
        self.calibration_params: Dict[str, Dict[str, Any]] = {}
        
        self.transform = get_default_transform(224)
        
        # Initialize neural backbone
        self._init_backbone()
    
    def _init_backbone(self):
        """Initialize frozen pretrained feature extractor with hooks."""
        # Clear existing hooks
        for h in self.hooks:
            h.remove()
        self.hooks = []
        
        base = None
        try:
            if self.backbone_name == "wide_resnet50_2":
                weights = models.Wide_ResNet50_2_Weights.DEFAULT
                base = models.wide_resnet50_2(weights=weights)
                self.feature_dim = 1536
            elif self.backbone_name == "resnet50":
                weights = models.ResNet50_Weights.DEFAULT
                base = models.resnet50(weights=weights)
                self.feature_dim = 1536
            else:
                weights = models.ResNet18_Weights.DEFAULT
                base = models.resnet18(weights=weights)
                self.feature_dim = 384
        except Exception as e:
            try:
                weights = models.ResNet18_Weights.DEFAULT
                base = models.resnet18(weights=weights)
                self.feature_dim = 384
            except Exception:
                if self.backbone_name == "wide_resnet50_2":
                    base = models.wide_resnet50_2(weights=None)
                    self.feature_dim = 1536
                else:
                    base = models.resnet18(weights=None)
                    self.feature_dim = 384

        for param in base.parameters():
            param.requires_grad = False
        base.eval()
        self.backbone = base.to(self.device)
        
        # Register forward hooks on target layers
        for layer_name in self.layers:
            if hasattr(self.backbone, layer_name):
                layer_module = getattr(self.backbone, layer_name)
                hook = layer_module.register_forward_hook(self._create_hook(layer_name))
                self.hooks.append(hook)
    
    def _create_hook(self, layer_name: str):
        """Create forward hook for intermediate feature extraction."""
        def hook(module, input_tensor, output_tensor):
            self.features[layer_name] = output_tensor
        return hook
    
    def extract_features(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass through backbone to capture hooked intermediate features."""
        with torch.no_grad():
            x = x.to(self.device)
            _ = self.backbone(x)
        return self.features
    
    def extract_scale_patches(
        self,
        features: Dict[str, torch.Tensor],
        patch_size: int
    ) -> Tuple[torch.Tensor, Tuple[int, int]]:
        """
        Extract spatial patch feature embeddings aligned across layers.
        Returns:
            patches: Tensor of shape (B * H * W, feature_dim)
            (H, W): spatial dimensions of layer2 grid
        """
        # Intermediate layers: layer2 and layer3
        l2 = features.get("layer2", None)
        l3 = features.get("layer3", None)
        
        if l2 is None or l3 is None:
            # Single layer fallback
            feat = list(features.values())[-1]
            pool = nn.AvgPool2d(kernel_size=patch_size, stride=1, padding=patch_size // 2)
            p_feat = pool(feat)
            b, c, h, w = p_feat.shape
            patches = p_feat.permute(0, 2, 3, 1).contiguous().view(-1, c)
            return patches, (h, w)
        
        # Patch neighborhood pooling
        pool = nn.AvgPool2d(kernel_size=patch_size, stride=1, padding=patch_size // 2)
        p2 = pool(l2)
        p3 = pool(l3)
        
        # Bilinear upsample layer3 to match layer2 spatial grid
        target_hw = p2.shape[-2:]
        p3_aligned = F.interpolate(p3, size=target_hw, mode="bilinear", align_corners=False)
        
        # Channel concatenation: [p2, p3_aligned]
        combined = torch.cat([p2, p3_aligned], dim=1)
        b, c, h, w = combined.shape
        self.feature_dim = c
        
        patches = combined.permute(0, 2, 3, 1).contiguous().view(-1, c)
        return patches, (h, w)
    
    def _coreset_sampling(
        self,
        patches: np.ndarray,
        target_size: int,
        max_candidate_pool: int = 40000,
        max_coreset_cap: int = 3000,
        random_seed: int = 42,
    ) -> np.ndarray:
        """
        Accelerated Greedy Minimax / k-center coreset selection algorithm.
        Subsamples diverse patches covering the feature manifold with O(N) vectorized updates.
        """
        n_samples = len(patches)
        if n_samples == 0:
            return patches

        np.random.seed(random_seed)
        if n_samples > max_candidate_pool:
            candidate_indices = np.random.choice(n_samples, max_candidate_pool, replace=False)
            candidate_patches = patches[candidate_indices]
        else:
            candidate_patches = patches

        n_candidates = len(candidate_patches)
        target_count = max(10, min(max_coreset_cap, min(target_size, n_candidates)))
        if target_count >= n_candidates:
            return candidate_patches

        feat_tensor = torch.from_numpy(candidate_patches).float()
        selected_indices = [int(np.random.choice(n_candidates))]

        first_center = feat_tensor[selected_indices[0]:selected_indices[0] + 1]
        min_sq_dists = torch.sum((feat_tensor - first_center) ** 2, dim=1)

        pbar = tqdm(total=target_count, desc="Minimax Coreset Selection", unit="patch", leave=False)
        pbar.update(1)

        for _ in range(1, target_count):
            new_idx = int(torch.argmax(min_sq_dists).item())
            selected_indices.append(new_idx)

            new_center = feat_tensor[new_idx:new_idx + 1]
            new_sq_dists = torch.sum((feat_tensor - new_center) ** 2, dim=1)
            min_sq_dists = torch.minimum(min_sq_dists, new_sq_dists)
            pbar.update(1)

        pbar.close()
        return candidate_patches[selected_indices]

    def build_memory_bank(
        self,
        normal_images: List[Union[str, Path]],
        batch_size: int = 32,
        num_workers: int = 0
    ):
        """Build multi-scale FAISS memory banks from normal training images."""
        print("=" * 70)
        print("Building Enhanced PatchCore Multi-Scale Memory Banks")
        print("=" * 70)

        dataset = ImageDataset(normal_images, transform=self.transform)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
        )

        # Single-pass forward extraction across all batches
        print(f"\n[Extracting intermediate layer features across {len(normal_images)} images...]")
        l2_batches, l3_batches = [], []
        with torch.no_grad():
            for batch in tqdm(dataloader, desc="Forward backbone extraction"):
                feats_dict = self.extract_features(batch)
                if "layer2" in feats_dict and "layer3" in feats_dict:
                    l2_batches.append(feats_dict["layer2"].cpu())
                    l3_batches.append(feats_dict["layer3"].cpu())
                else:
                    first_feat = list(feats_dict.values())[-1]
                    l2_batches.append(first_feat.cpu())
                    l3_batches.append(first_feat.cpu())

        for patch_size in self.patch_sizes:
            print(f"\n[Memory Bank {patch_size}x{patch_size}]")
            print("-" * 70)

            all_patches = []
            pool = nn.AvgPool2d(kernel_size=patch_size, stride=1, padding=patch_size // 2)

            for l2, l3 in zip(l2_batches, l3_batches):
                p2 = pool(l2)
                p3 = pool(l3)
                target_hw = p2.shape[-2:]
                p3_aligned = F.interpolate(p3, size=target_hw, mode="bilinear", align_corners=False)
                combined = torch.cat([p2, p3_aligned], dim=1)
                b, c, h, w = combined.shape
                self.feature_dim = c
                patches = combined.permute(0, 2, 3, 1).contiguous().view(-1, c)
                all_patches.append(patches.numpy().astype(np.float32))

            if not all_patches:
                continue

            combined_patches = np.concatenate(all_patches, axis=0)
            print(f"  Extracted {len(combined_patches)} raw patches (dim={combined_patches.shape[1]})")

            # Dimension reduction
            if self.dimension_reduction and combined_patches.shape[1] > self.target_dim:
                print(f"  Applying SparseRandomProjection: {combined_patches.shape[1]} -> {self.target_dim}")
                projector = SparseRandomProjection(n_components=self.target_dim, random_state=42)
                reduced_patches = projector.fit_transform(combined_patches).astype(np.float32)
                self.projectors[patch_size] = projector
            else:
                reduced_patches = combined_patches
                self.projectors[patch_size] = None

            # Coreset subsampling
            target_size = max(10, int(len(reduced_patches) * self.coreset_ratio))
            print(f"  Coreset sampling: {len(reduced_patches)} -> {target_size} patches")
            coreset = self._coreset_sampling(reduced_patches, target_size)

            # Build FAISS index
            dim = coreset.shape[1]
            coreset_np = np.ascontiguousarray(coreset, dtype=np.float32)

            if faiss is not None:
                index = faiss.IndexFlatL2(dim)
                index.add(coreset_np)
            else:
                from sklearn.neighbors import NearestNeighbors
                index = NearestNeighbors(n_neighbors=1, metric="euclidean")
                index.fit(coreset_np)

            self.memory_banks[patch_size] = {
                "index": index,
                "coreset": coreset_np,
                "dimension": dim,
                "num_patches": len(coreset_np)
            }

            print(f"  [OK] Memory bank ({patch_size}x{patch_size}) built: {len(coreset_np)} patches, dim={dim}")

        print("\n" + "=" * 70)
        print(f"All {len(self.memory_banks)} scale memory banks built successfully!")
        print("=" * 70)
    
    def predict_raw_multiscale(
        self,
        image: Union[np.ndarray, Image.Image]
    ) -> Tuple[Dict[str, float], float, np.ndarray]:
        """
        Run multi-scale PatchCore inference on a single image.
        Returns:
            scores: dict of raw L2 distances per patch scale + ensemble
            ensemble_distance: weighted ensemble anomaly distance
            anomaly_map: 2D smoothed heatmap
        """
        if not self.memory_banks:
            return {"ensemble": 0.0}, 0.0, np.zeros((224, 224), dtype=np.float32)
        
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
        
        scores: Dict[str, float] = {}
        heatmaps = []
        
        with torch.no_grad():
            features_dict = self.extract_features(tensor)
            
            for patch_size, bank_info in self.memory_banks.items():
                patches, (fh, fw) = self.extract_scale_patches(features_dict, patch_size)
                feat_np = patches.cpu().numpy().astype(np.float32)
                
                # Apply projection if exists
                projector = self.projectors.get(patch_size, None)
                if projector is not None and feat_np.shape[1] != bank_info["dimension"]:
                    try:
                        feat_np = projector.transform(feat_np).astype(np.float32)
                    except Exception:
                        pass
                
                # FAISS search
                idx = bank_info["index"]
                if faiss is not None and isinstance(idx, faiss.Index):
                    distances, _ = idx.search(np.ascontiguousarray(feat_np, dtype=np.float32), 1)
                    patch_dists = np.sqrt(np.maximum(0.0, distances[:, 0]))
                elif hasattr(idx, "kneighbors"):
                    distances, _ = idx.kneighbors(feat_np, n_neighbors=1)
                    patch_dists = distances[:, 0]
                else:
                    diff = feat_np[:, None, :] - bank_info["coreset"][None, :, :]
                    dists = np.linalg.norm(diff, axis=-1)
                    patch_dists = np.min(dists, axis=-1)
                
                scale_score = float(np.max(patch_dists))
                scores[f"patch_{patch_size}"] = scale_score
                
                score_map = patch_dists.reshape(fh, fw)
                heatmaps.append(score_map)
        
        # Multi-scale ensemble score calculation
        weighted_sum = 0.0
        total_weight = 0.0
        for ps in self.patch_sizes:
            key = f"patch_{ps}"
            if key in scores:
                w = self.patch_weights.get(key, 1.0)
                weighted_sum += scores[key] * w
                total_weight += w
        
        ensemble_distance = float(weighted_sum / total_weight) if total_weight > 0 else 0.0
        scores["ensemble"] = ensemble_distance
        
        # Average heatmap across scales and smooth
        if heatmaps:
            avg_map = np.mean(np.stack(heatmaps, axis=0), axis=0)
            if cv2 is not None:
                smoothed = cv2.GaussianBlur(avg_map, (0, 0), sigmaX=self.sigma, sigmaY=self.sigma)
                resized_map = cv2.resize(smoothed, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
            else:
                from scipy.ndimage import gaussian_filter, zoom
                smoothed = gaussian_filter(avg_map, sigma=self.sigma)
                zoom_h = orig_h / smoothed.shape[0]
                zoom_w = orig_w / smoothed.shape[1]
                resized_map = zoom(smoothed, (zoom_h, zoom_w), order=1)
        else:
            resized_map = np.zeros((orig_h, orig_w), dtype=np.float32)
        
        return scores, ensemble_distance, resized_map
    
    def predict(self, image: Union[np.ndarray, Image.Image, torch.Tensor]) -> Dict[str, float]:
        """Predict anomaly scores for an image across all scales and ensemble."""
        if isinstance(image, torch.Tensor):
            # Convert tensor back to numpy uint8 for standard pipeline
            img_np = image.squeeze(0).permute(1, 2, 0).cpu().numpy()
            img_np = ((img_np * [0.229, 0.224, 0.225] + [0.485, 0.456, 0.406]) * 255).clip(0, 255).astype(np.uint8)
            scores, _, _ = self.predict_raw_multiscale(img_np)
            return scores
        
        scores, _, _ = self.predict_raw_multiscale(image)
        return scores
    
    def extract_bounding_box(self, anomaly_map: np.ndarray, threshold: float = 0.50) -> Optional[Tuple[float, float, float, float]]:
        """Extract bounding box around the most anomalous region in the heatmap."""
        h, w = anomaly_map.shape[:2]
        denom = anomaly_map.max() - anomaly_map.min() + 1e-8
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
    
    def predict_signals(self, frame: np.ndarray) -> List[CalibratedSignal]:
        """
        Run inference on image frame and return contract-compliant CalibratedSignal.
        """
        if not self.memory_banks:
            return []
        
        h, w = frame.shape[:2]
        scores, ensemble_dist, anomaly_map = self.predict_raw_multiscale(frame)
        
        # Scale through calibrated sigmoid parameters
        calib = self.calibration_params.get("ensemble", {})
        threshold = calib.get("threshold", 10.0)
        k = calib.get("sigmoid_k", 0.5)
        b = calib.get("sigmoid_b", 0.0)
        
        calibrated_prob = float(expit(k * (ensemble_dist - threshold) + b))
        fired = bool(calibrated_prob >= self.threshold)
        
        bbox = None
        if fired:
            bbox = self.extract_bounding_box(anomaly_map, threshold=0.45)
        
        signal = CalibratedSignal(
            stream_name="patchcore_anomaly",
            raw_score=ensemble_dist,
            calibrated_prob=calibrated_prob,
            predicted_class=DefectClass.VISUAL_ANOMALY,
            is_anomaly=fired,
            signal_type=SignalType.VISUAL_NOVEL,
            threshold=self.threshold,
            bbox=bbox,
            explanation=f"PatchCore multi-scale detected anomaly with score {calibrated_prob:.1%} (raw L2: {ensemble_dist:.2f})",
            metadata={
                "raw_distance": ensemble_dist,
                "calibrated_score": calibrated_prob,
                "multiscale_scores": scores,
                "image_width": w,
                "image_height": h,
            },
        )
        return [signal]
    
    def calibrate(self, normal_images: List[Union[str, Path]], target_fpr: float = 0.01):
        """Calibrate statistical thresholds and fit sigmoid loss on normal validation images."""
        print("\n" + "=" * 70)
        print("Calibrating PatchCore Multi-Scale Thresholds")
        print("=" * 70)
        
        all_scores: Dict[str, List[float]] = {f"patch_{ps}": [] for ps in self.patch_sizes}
        all_scores["ensemble"] = []
        
        for img_path in tqdm(normal_images, desc="Evaluating validation normals"):
            try:
                pil_img = Image.open(img_path).convert("RGB")
                scores, _, _ = self.predict_raw_multiscale(pil_img)
                for key, val in scores.items():
                    if key in all_scores:
                        all_scores[key].append(val)
            except Exception:
                continue
        
        for key, scores_list in all_scores.items():
            if not scores_list:
                continue
            scores_array = np.array(scores_list)
            threshold = float(np.percentile(scores_array, (1.0 - target_fpr) * 100))
            
            def sigmoid_loss(params, s_arr, thresh):
                k_val, b_val = params
                probs = expit(k_val * (s_arr - thresh) + b_val)
                # Keep probability low for normal validation samples
                return float(np.mean(-np.log(1.0 - probs + 1e-6)))
            
            result = minimize(
                sigmoid_loss,
                x0=[0.5, 0.0],
                args=(scores_array, threshold),
                method="Nelder-Mead"
            )
            
            k_opt, b_opt = float(result.x[0]), float(result.x[1])
            
            self.calibration_params[key] = {
                "threshold": threshold,
                "sigmoid_k": k_opt,
                "sigmoid_b": b_opt,
                "mean": float(scores_array.mean()),
                "std": float(scores_array.std()),
                "p99": float(np.percentile(scores_array, 99.0)),
                "target_fpr": target_fpr
            }
            
            print(f"  {key:12s}: threshold={threshold:6.2f}, k={k_opt:5.2f}, b={b_opt:5.2f}, mean={scores_array.mean():5.2f}")
        
        print("\n" + "=" * 70)
        print("Multi-scale calibration complete!")
        print("=" * 70)
    
    def save(self, save_dir: Union[str, Path]):
        """Save memory bank indices, projector components, calibration, and config."""
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save memory banks
        for patch_size, bank in self.memory_banks.items():
            coreset = bank["coreset"]
            npz_path = save_path / f"memory_bank_{patch_size}.npz"
            save_dict = {
                "coreset": coreset,
                "patch_size": patch_size,
                "dimension": bank["dimension"],
            }
            projector = self.projectors.get(patch_size, None)
            if projector is not None and hasattr(projector, "components_"):
                comps = projector.components_
                save_dict["projector_components"] = comps.toarray() if hasattr(comps, "toarray") else comps
            np.savez_compressed(npz_path, **save_dict)
            
            # Save FAISS index file if available
            if faiss is not None and isinstance(bank["index"], faiss.Index):
                index_path = save_path / f"memory_bank_{patch_size}.index"
                faiss.write_index(bank["index"], str(index_path))
        
        # Save calibration
        calib_path = save_path / "calibration.json"
        with open(calib_path, "w", encoding="utf-8") as f:
            json.dump(self.calibration_params, f, indent=2)
        
        # Save config
        config = {
            "backbone": self.backbone_name,
            "layers": self.layers,
            "patch_sizes": self.patch_sizes,
            "coreset_ratio": self.coreset_ratio,
            "dimension_reduction": self.dimension_reduction,
            "target_dim": self.target_dim,
            "patch_weights": self.patch_weights,
            "sigma": self.sigma,
            "threshold": self.threshold
        }
        config_path = save_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        
        print(f"[OK] Enhanced PatchCore saved to: {save_path}")
    
    def load(self, load_dir: Union[str, Path]):
        """Load memory banks, projectors, calibration, and configuration from directory."""
        load_path = Path(load_dir)
        if not load_path.exists():
            raise FileNotFoundError(f"Directory not found: {load_path}")
        
        config_path = load_path / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.backbone_name = config.get("backbone", self.backbone_name)
            self.layers = config.get("layers", self.layers)
            self.patch_sizes = config.get("patch_sizes", self.patch_sizes)
            self.coreset_ratio = config.get("coreset_ratio", self.coreset_ratio)
            self.dimension_reduction = config.get("dimension_reduction", self.dimension_reduction)
            self.target_dim = config.get("target_dim", self.target_dim)
            self.patch_weights = config.get("patch_weights", self.patch_weights)
            self.sigma = config.get("sigma", self.sigma)
            self.threshold = config.get("threshold", self.threshold)
        
        # Re-initialize backbone
        self._init_backbone()
        
        # Load memory banks per patch scale
        self.memory_banks = {}
        self.projectors = {}
        
        for patch_size in self.patch_sizes:
            npz_path = load_path / f"memory_bank_{patch_size}.npz"
            index_path = load_path / f"memory_bank_{patch_size}.index"
            
            if npz_path.exists():
                data = np.load(npz_path, allow_pickle=True)
                coreset = data["coreset"]
                dim = int(data.get("dimension", coreset.shape[1]))
                
                # Restore projector if present
                if "projector_components" in data:
                    comps = data["projector_components"]
                    proj = SparseRandomProjection(n_components=comps.shape[0])
                    proj.components_ = comps
                    self.projectors[patch_size] = proj
                else:
                    self.projectors[patch_size] = None
                
                # Load or rebuild FAISS index
                if index_path.exists() and faiss is not None:
                    try:
                        index = faiss.read_index(str(index_path))
                    except Exception:
                        index = faiss.IndexFlatL2(dim)
                        index.add(np.ascontiguousarray(coreset, dtype=np.float32))
                elif faiss is not None:
                    index = faiss.IndexFlatL2(dim)
                    index.add(np.ascontiguousarray(coreset, dtype=np.float32))
                else:
                    from sklearn.neighbors import NearestNeighbors
                    index = NearestNeighbors(n_neighbors=1, metric="euclidean")
                    index.fit(coreset)
                
                self.memory_banks[patch_size] = {
                    "index": index,
                    "coreset": coreset,
                    "dimension": dim,
                    "num_patches": len(coreset)
                }
        
        # Load calibration
        calib_path = load_path / "calibration.json"
        if calib_path.exists():
            with open(calib_path, "r", encoding="utf-8") as f:
                self.calibration_params = json.load(f)
        
        print(f"[OK] Enhanced PatchCore loaded from: {load_path} ({len(self.memory_banks)} scales)")
