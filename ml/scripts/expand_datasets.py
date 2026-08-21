"""
TrackChain Master Dataset Expansion & Synthesis Module.
Unified dataset preparation pipeline for:
  1. YOLO Defect Detection (Multi-source aggregation + aggressive railway augmentations)
  2. PatchCore Anomaly Detection (Procedural track synthesis + normal augmentation + KMeans diversity)
"""

import argparse
import os
import sys
import json
import random
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

import cv2
import numpy as np
from tqdm import tqdm
import yaml

# Ensure project root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    import albumentations as A
except ImportError:
    A = None

from ml.core.registry import ModelRegistry


CLASS_MAPPING = {
    'missing_fastener': 0,
    'defective_clip': 1,
    'crack': 2,
    'obstruction': 3,
}
CLASS_NAMES = ['missing_fastener', 'defective_clip', 'crack', 'obstruction']


# ============================================================================
# Shared Geometry & Bounding Box Utilities
# ============================================================================

def sanitize_bbox(bbox: List[float]) -> Optional[List[float]]:
    """Sanitize and clamp YOLO bbox coordinates [x_center, y_center, width, height]."""
    if len(bbox) < 4:
        return None
    
    x, y, w, h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    
    if w <= 0.005 or h <= 0.005:
        return None
    
    x = max(0.01, min(0.99, x))
    y = max(0.01, min(0.99, y))
    w = max(0.01, min(1.0, w))
    h = max(0.01, min(1.0, h))
    
    half_w = w / 2.0
    half_h = h / 2.0
    
    x1 = max(0.0, x - half_w)
    y1 = max(0.0, y - half_h)
    x2 = min(1.0, x + half_w)
    y2 = min(1.0, y + half_h)
    
    new_w = x2 - x1
    new_h = y2 - y1
    
    if new_w <= 0.005 or new_h <= 0.005:
        return None
    
    new_x = (x1 + x2) / 2.0
    new_y = (y1 + y2) / 2.0
    
    return [new_x, new_y, new_w, new_h]


# ============================================================================
# Section 1: YOLO Augmentation & Dataset Expansion
# ============================================================================

class _SimpleYoloTransform:
    def __init__(self, fn, uses_bbox=False):
        self.fn = fn
        self.uses_bbox = uses_bbox

    def __call__(self, image=None, bboxes=None, class_labels=None, **kwargs):
        img = image if image is not None else kwargs.get("image")
        boxes = bboxes if bboxes is not None else kwargs.get("bboxes", [])
        labels = class_labels if class_labels is not None else kwargs.get("class_labels", [])
        if img is None:
            return {"image": img, "bboxes": boxes, "class_labels": labels}
        res_img, res_boxes = self.fn(img, boxes)
        return {"image": res_img, "bboxes": res_boxes, "class_labels": labels}


def _fallback_yolo_basic(img: np.ndarray, bboxes: List[List[float]]) -> Tuple[np.ndarray, List[List[float]]]:
    if np.random.rand() > 0.5:
        img = cv2.flip(img, 1)
        new_boxes = []
        for box in bboxes:
            new_box = [1.0 - box[0], box[1], box[2], box[3]]
            new_boxes.append(new_box)
        return img, new_boxes
    return img, bboxes


def _fallback_yolo_lighting(img: np.ndarray, bboxes: List[List[float]]) -> Tuple[np.ndarray, List[List[float]]]:
    alpha = float(np.random.uniform(0.8, 1.2))
    beta = float(np.random.uniform(-20, 20))
    img = np.clip(img.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)
    return img, bboxes


def _fallback_yolo_weather(img: np.ndarray, bboxes: List[List[float]]) -> Tuple[np.ndarray, List[List[float]]]:
    noise = np.random.normal(0, 8, img.shape)
    img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return img, bboxes


def _fallback_yolo_motion(img: np.ndarray, bboxes: List[List[float]]) -> Tuple[np.ndarray, List[List[float]]]:
    k = int(np.random.choice([3, 5]))
    img = cv2.GaussianBlur(img, (k, k), 0)
    return img, bboxes


def _fallback_yolo_geometric(img: np.ndarray, bboxes: List[List[float]]) -> Tuple[np.ndarray, List[List[float]]]:
    return img, bboxes


def _fallback_yolo_occlusion(img: np.ndarray, bboxes: List[List[float]]) -> Tuple[np.ndarray, List[List[float]]]:
    h, w = img.shape[:2]
    rx = np.random.randint(0, max(1, w - 20))
    ry = np.random.randint(0, max(1, h - 20))
    img = img.copy()
    img[ry:ry+15, rx:rx+15] = 0
    return img, bboxes


def create_railway_augmentation_pipeline():
    """Create aggressive augmentation pipeline for railway defect detection."""
    if A is None:
        return {
            'basic': (_SimpleYoloTransform(_fallback_yolo_basic, uses_bbox=True), True),
            'lighting': (_SimpleYoloTransform(_fallback_yolo_lighting, uses_bbox=False), False),
            'weather': (_SimpleYoloTransform(_fallback_yolo_weather, uses_bbox=False), False),
            'motion': (_SimpleYoloTransform(_fallback_yolo_motion, uses_bbox=False), False),
            'geometric': (_SimpleYoloTransform(_fallback_yolo_geometric, uses_bbox=True), True),
            'occlusion': (_SimpleYoloTransform(_fallback_yolo_occlusion, uses_bbox=False), False),
        }
    
    basic_transforms = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.3),
        A.RandomRotate90(p=0.3),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.1))
    
    lighting_transforms = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.35, p=0.7),
        A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=25, val_shift_limit=20, p=0.5),
        A.CLAHE(clip_limit=3.0, tile_grid_size=(8, 8), p=0.3),
    ])
    
    weather_transforms = A.Compose([
        A.RandomRain(slant_range=(-10, 10), drop_length=15, drop_width=1, drop_color=(200, 200, 200), blur_value=2, brightness_coefficient=0.8, p=0.25),
    ])
    
    motion_transforms = A.Compose([
        A.MotionBlur(blur_limit=7, p=0.4),
        A.GaussianBlur(blur_limit=5, p=0.3),
        A.GaussNoise(p=0.3),
    ])
    
    geometric_transforms = A.Compose([
        A.Affine(scale=(0.85, 1.15), translate_percent=(-0.08, 0.08), rotate=(-12, 12), shear=(-4, 4), p=0.5),
        A.Perspective(scale=(0.04, 0.08), p=0.3),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.1))
    
    occlusion_transforms = A.Compose([
        A.CoarseDropout(num_holes_range=(2, 6), hole_height_range=(8, 24), hole_width_range=(8, 24), fill=0, p=0.35),
    ])
    
    return {
        'basic': (basic_transforms, True),
        'lighting': (lighting_transforms, False),
        'weather': (weather_transforms, False),
        'motion': (motion_transforms, False),
        'geometric': (geometric_transforms, True),
        'occlusion': (occlusion_transforms, False),
    }


def augment_sample(image: np.ndarray, bboxes: List[Dict], pipelines: Dict) -> Tuple[np.ndarray, List[Dict]]:
    """Apply random combination of augmentation pipelines while preserving valid bboxes."""
    if pipelines is None or not bboxes:
        return image, bboxes
    
    num_levels = random.randint(2, 4)
    selected_keys = random.sample(list(pipelines.keys()), num_levels)
    
    current_img = image.copy()
    bbox_coords = [b['bbox'] for b in bboxes]
    class_labels = [b['class_id'] for b in bboxes]
    
    for key in selected_keys:
        pipeline, uses_bbox = pipelines[key]
        try:
            if uses_bbox:
                transformed = pipeline(image=current_img, bboxes=bbox_coords, class_labels=class_labels)
                if transformed['bboxes'] and len(transformed['bboxes']) == len(class_labels):
                    current_img = transformed['image']
                    bbox_coords = transformed['bboxes']
                    class_labels = transformed['class_labels']
            else:
                transformed = pipeline(image=current_img)
                current_img = transformed['image']
        except Exception:
            continue
    
    augmented_bboxes = []
    for cls, raw_box in zip(class_labels, bbox_coords):
        clean_box = sanitize_bbox(raw_box)
        if clean_box is not None:
            augmented_bboxes.append({'class_id': cls, 'bbox': clean_box})
    
    if not augmented_bboxes:
        return current_img, bboxes
    
    return current_img, augmented_bboxes


def expand_dataset(
    data_root: str = "data/external/rail_defects",
    output_root: str = "data/external/rail_defects_expanded",
    target_per_class: int = 250,
    augment_factor: int = 10,
    train_ratio: float = 0.80,
    val_ratio: float = 0.15,
) -> Dict[str, Any]:
    """Execute complete dataset expansion and generation for YOLO."""
    abs_data_root = Path(data_root) if Path(data_root).is_absolute() else repo_root / data_root
    abs_output_root = Path(output_root) if Path(output_root).is_absolute() else repo_root / output_root
    abs_output_root.mkdir(parents=True, exist_ok=True)
    
    for split in ['train', 'valid', 'test']:
        (abs_output_root / split / 'images').mkdir(parents=True, exist_ok=True)
        (abs_output_root / split / 'labels').mkdir(parents=True, exist_ok=True)
    
    # Load original samples
    samples = []
    for split in ['train', 'valid', 'test']:
        img_dir = abs_data_root / split / 'images'
        lbl_dir = abs_data_root / split / 'labels'
        if not img_dir.exists():
            continue
        for img_p in sorted(list(img_dir.glob('*.jpg')) + list(img_dir.glob('*.png'))):
            lbl_p = lbl_dir / (img_p.stem + '.txt')
            bboxes = []
            if lbl_p.exists():
                with open(lbl_p, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            clean = sanitize_bbox([float(x) for x in parts[1:5]])
                            if clean:
                                bboxes.append({'class_id': int(parts[0]), 'bbox': clean})
            if bboxes:
                samples.append({'image_path': str(img_p), 'bboxes': bboxes, 'source': 'original'})
    
    pipelines = create_railway_augmentation_pipeline()
    augmented_samples = []
    
    for sample in tqdm(samples, desc="Augmenting YOLO dataset"):
        img = cv2.imread(sample['image_path'])
        if img is None:
            continue
        augmented_samples.append(sample)
        for _ in range(augment_factor):
            aug_img, aug_boxes = augment_sample(img, sample['bboxes'], pipelines)
            if aug_boxes:
                augmented_samples.append({
                    'image': aug_img,
                    'bboxes': aug_boxes,
                    'source': 'augmented'
                })
    
    random.seed(42)
    random.shuffle(augmented_samples)
    
    total = len(augmented_samples)
    n_train = int(total * train_ratio)
    n_val = int(total * val_ratio)
    
    splits = {
        'train': augmented_samples[:n_train],
        'valid': augmented_samples[n_train:n_train + n_val],
        'test': augmented_samples[n_train + n_val:]
    }
    
    sample_id = 0
    for split_name, split_samples in splits.items():
        out_img_dir = abs_output_root / split_name / 'images'
        out_lbl_dir = abs_output_root / split_name / 'labels'
        for s in split_samples:
            sample_id += 1
            img_name = f"img_{sample_id:06d}.jpg"
            lbl_name = f"img_{sample_id:06d}.txt"
            
            if 'image' in s:
                cv2.imwrite(str(out_img_dir / img_name), s['image'])
            else:
                shutil.copy(s['image_path'], out_img_dir / img_name)
            
            with open(out_lbl_dir / lbl_name, 'w', encoding='utf-8') as f:
                for b in s['bboxes']:
                    box = b['bbox']
                    f.write(f"{b['class_id']} {box[0]:.6f} {box[1]:.6f} {box[2]:.6f} {box[3]:.6f}\n")
    
    data_yaml = {
        'path': abs_output_root.resolve().as_posix(),
        'train': 'train/images',
        'val': 'valid/images',
        'test': 'test/images',
        'nc': 4,
        'names': ['missing_fastener', 'defective_clip', 'crack', 'obstruction']
    }
    with open(abs_output_root / 'data.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(data_yaml, f, sort_keys=False)
    
    return {'total': total, 'train': len(splits['train']), 'valid': len(splits['valid']), 'test': len(splits['test'])}


# ============================================================================
# Section 2: PatchCore Normal Augmentation & Dataset Expansion
# ============================================================================

class _SimpleNormalTransform:
    def __init__(self, fn):
        self.fn = fn
    def __call__(self, image=None, **kwargs):
        img = image if image is not None else kwargs.get("image")
        if img is None:
            return {"image": img}
        return {"image": self.fn(img)}


def _fallback_lighting(img: np.ndarray) -> np.ndarray:
    alpha = float(np.random.uniform(0.75, 1.25))
    beta = float(np.random.uniform(-25, 25))
    return np.clip(img.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)


def _fallback_weather(img: np.ndarray) -> np.ndarray:
    noise = np.random.normal(0, 8, img.shape)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def _fallback_geometric(img: np.ndarray) -> np.ndarray:
    if np.random.rand() > 0.5:
        img = cv2.flip(img, 1)
    return img


def _fallback_texture(img: np.ndarray) -> np.ndarray:
    k = int(np.random.choice([3, 5]))
    return cv2.GaussianBlur(img, (k, k), 0)


def _fallback_color(img: np.ndarray) -> np.ndarray:
    try:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * np.random.uniform(0.8, 1.2), 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    except Exception:
        return img


def create_normal_augmentation_pipeline():
    """Create augmentation pipeline for normal track images."""
    if A is None:
        return {
            'lighting': _SimpleNormalTransform(_fallback_lighting),
            'weather': _SimpleNormalTransform(_fallback_weather),
            'geometric': _SimpleNormalTransform(_fallback_geometric),
            'texture': _SimpleNormalTransform(_fallback_texture),
            'color': _SimpleNormalTransform(_fallback_color),
        }
    
    lighting = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.35, p=0.7),
        A.CLAHE(clip_limit=3.0, tile_grid_size=(8, 8), p=0.3),
        A.RandomGamma(gamma_limit=(80, 120), p=0.3),
    ])
    
    weather = A.Compose([
        A.RandomRain(slant_range=(-10, 10), drop_length=15, drop_width=1, drop_color=(180, 180, 180), blur_value=2, brightness_coefficient=0.8, p=0.20),
    ])
    
    geometric = A.Compose([
        A.Affine(scale=(0.92, 1.08), translate_percent=(-0.05, 0.05), rotate=(-5, 5), shear=(-2, 2), p=0.5),
        A.Perspective(scale=(0.02, 0.05), p=0.2),
        A.HorizontalFlip(p=0.5),
    ])
    
    texture = A.Compose([
        A.GaussianBlur(blur_limit=3, p=0.3),
        A.MotionBlur(blur_limit=5, p=0.2),
        A.MedianBlur(blur_limit=3, p=0.2),
    ])
    
    color = A.Compose([
        A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=25, val_shift_limit=25, p=0.5),
        A.ToGray(p=0.05),
    ])
    
    return {
        'lighting': lighting,
        'weather': weather,
        'geometric': geometric,
        'texture': texture,
        'color': color,
    }


def generate_track_pattern(width: int = 640, height: int = 640) -> np.ndarray:
    """Generate a high-fidelity procedural synthetic normal railway track pattern."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    ballast_color = np.array([80, 75, 65], dtype=np.float32)
    noise = np.random.normal(0, 18, (height, width, 3))
    img[:] = np.clip(ballast_color + noise, 0, 255).astype(np.uint8)
    
    sleeper_spacing = 60
    sleeper_height = 24
    for y in range(10, height, sleeper_spacing):
        color_variation = np.random.randint(-10, 10)
        sleeper_color = (
            max(0, min(255, 60 + color_variation)),
            max(0, min(255, 55 + color_variation)),
            max(0, min(255, 50 + color_variation))
        )
        cv2.rectangle(img, (int(width * 0.15), y), (int(width * 0.85), y + sleeper_height), sleeper_color, -1)

    rail_width = 24
    rail_spacing = int(width * 0.35)
    center_x = width // 2
    for offset in [center_x - rail_spacing // 2, center_x + rail_spacing // 2]:
        cv2.rectangle(img, (offset - rail_width // 2, 0), (offset + rail_width // 2, height), (50, 50, 55), -1)
        cv2.line(img, (offset - rail_width // 6, 0), (offset - rail_width // 6, height), (130, 130, 140), 3)
    return img


def augment_normal_image(image: np.ndarray, pipelines: Dict, num_augmentations: int = 5) -> List[np.ndarray]:
    """Generate multiple augmented versions of a normal image."""
    augmented = [image]
    if not pipelines:
        return augmented
    for _ in range(num_augmentations - 1):
        num_types = random.randint(2, 3)
        available_keys = list(pipelines.keys())
        selected = random.sample(available_keys, min(num_types, len(available_keys)))
        aug_img = image.copy()
        for aug_type in selected:
            try:
                aug_img = pipelines[aug_type](image=aug_img)['image']
            except Exception:
                continue
        augmented.append(aug_img)
    return augmented


def ensure_diversity(images: List[Path], target_count: int, num_clusters: int = 30) -> List[Path]:
    """Sample diverse subset from images."""
    if len(images) <= target_count:
        return images
    try:
        from sklearn.cluster import KMeans
        features = []
        valid_images = []
        for p in images:
            img = cv2.imread(str(p))
            if img is not None:
                small = cv2.resize(img, (32, 32)).flatten()
                features.append(small)
                valid_images.append(p)
        if len(valid_images) <= target_count:
            return valid_images
        kmeans = KMeans(n_clusters=min(num_clusters, len(valid_images)), random_state=42, n_init='auto')
        labels = kmeans.fit_predict(features)
        selected = []
        for k in range(min(num_clusters, len(valid_images))):
            cluster_indices = np.where(labels == k)[0]
            if len(cluster_indices) > 0:
                selected.append(valid_images[random.choice(cluster_indices)])
        remaining = [p for p in valid_images if p not in selected]
        needed = target_count - len(selected)
        if needed > 0 and remaining:
            selected.extend(random.sample(remaining, min(needed, len(remaining))))
        return selected[:target_count]
    except Exception:
        return random.sample(images, target_count)


def expand_patchcore_dataset(
    normal_data_root: str = "data/external/rail_normal_only",
    output_root: str = "data/external/rail_normal_expanded",
    target_count: int = 800,
    augment_factor: int = 8,
) -> Dict[str, Any]:
    """Execute complete dataset expansion for PatchCore with train/valid/test and defect validation splits."""
    abs_norm = Path(normal_data_root) if Path(normal_data_root).is_absolute() else repo_root / normal_data_root
    abs_out = Path(output_root) if Path(output_root).is_absolute() else repo_root / output_root
    abs_out.mkdir(parents=True, exist_ok=True)

    for split in ['train/good', 'valid/good', 'test/good', 'valid/defect']:
        (abs_out / split).mkdir(parents=True, exist_ok=True)

    # Collect existing normals
    existing = list(abs_norm.glob('**/*.jpg')) + list(abs_norm.glob('**/*.png')) if abs_norm.exists() else []
    pipelines = create_normal_augmentation_pipeline()

    all_normals = []
    idx = 0
    for p in existing:
        img = cv2.imread(str(p))
        if img is None:
            continue
        variants = augment_normal_image(img, pipelines, num_augmentations=augment_factor)
        for v in variants:
            idx += 1
            all_normals.append(v)

    # Add procedurally synthesized tracks if count below target
    while len(all_normals) < target_count:
        idx += 1
        syn_img = generate_track_pattern()
        all_normals.append(syn_img)

    random.seed(42)
    random.shuffle(all_normals)

    # Split normal samples: 80% train, 10% valid, 10% test
    n_total = len(all_normals)
    n_val = max(50, int(n_total * 0.10))
    n_test = max(50, int(n_total * 0.10))
    n_train = n_total - n_val - n_test

    train_normals = all_normals[:n_train]
    val_normals = all_normals[n_train:n_train + n_val]
    test_normals = all_normals[n_train + n_val:]

    for i, img in enumerate(train_normals):
        cv2.imwrite(str(abs_out / 'train' / 'good' / f"norm_train_{i+1:05d}.jpg"), img)
    for i, img in enumerate(val_normals):
        cv2.imwrite(str(abs_out / 'valid' / 'good' / f"norm_val_{i+1:05d}.jpg"), img)
    for i, img in enumerate(test_normals):
        cv2.imwrite(str(abs_out / 'test' / 'good' / f"norm_test_{i+1:05d}.jpg"), img)

    # Populate valid/defect with defect validation images
    defect_sources = [
        repo_root / "data" / "external" / "rail_defects_expanded" / "valid" / "images",
        repo_root / "data" / "external" / "rail_defects_synthetic" / "valid" / "images",
        repo_root / "data" / "external" / "rail_defects" / "valid" / "images",
        repo_root / "data" / "external" / "rail_defects_expanded" / "test" / "images",
        repo_root / "data" / "external" / "rail_defects" / "test" / "images",
    ]

    defect_imgs = []
    for d_src in defect_sources:
        if d_src.exists():
            defect_imgs.extend(list(d_src.glob("*.jpg")) + list(d_src.glob("*.png")))

    num_defects_copied = 0
    if defect_imgs:
        random.seed(42)
        selected_defects = random.sample(defect_imgs, min(150, len(defect_imgs)))
        for i, d_path in enumerate(selected_defects):
            dst = abs_out / 'valid' / 'defect' / f"defect_{i+1:05d}.jpg"
            shutil.copy(d_path, dst)
            num_defects_copied += 1

    # Create dataset config
    cfg = {
        'path': abs_out.resolve().as_posix(),
        'train': 'train/good',
        'valid': 'valid/good',
        'test': 'test/good',
        'defect_valid': 'valid/defect',
        'normal_count': {'train': len(train_normals), 'valid': len(val_normals), 'test': len(test_normals)},
        'defect_count': {'valid': num_defects_copied},
    }
    with open(abs_out / 'dataset_config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, sort_keys=False)

    print(f"[OK] PatchCore dataset expanded: train={len(train_normals)}, valid={len(val_normals)}, test={len(test_normals)}, defect_valid={num_defects_copied}")
    return {'train': len(train_normals), 'valid': len(val_normals), 'defect_valid': num_defects_copied}


# Backwards compatibility alias
expand_yolo_dataset = expand_dataset


# ============================================================================
# Main CLI
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrackChain Unified Dataset Expansion Tool.")
    parser.add_argument("--mode", choices=["all", "yolo", "patchcore"], default="all", help="Dataset expansion target")
    parser.add_argument("--yolo-data", default="data/external/rail_defects", help="Original YOLO defect data root")
    parser.add_argument("--yolo-output", default="data/external/rail_defects_expanded", help="Output expanded YOLO directory")
    parser.add_argument("--patchcore-data", default="data/external/rail_normal_only", help="Original normal data root")
    parser.add_argument("--patchcore-output", default="data/external/rail_normal_expanded", help="Output expanded PatchCore directory")
    args = parser.parse_args()

    if args.mode in ["all", "yolo"]:
        print("[INFO] Expanding YOLO dataset...")
        expand_dataset(data_root=args.yolo_data, output_root=args.yolo_output)
    if args.mode in ["all", "patchcore"]:
        print("[INFO] Expanding PatchCore dataset...")
        expand_patchcore_dataset(normal_data_root=args.patchcore_data, output_root=args.patchcore_output)
