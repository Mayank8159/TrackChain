"""
Master script to aggregate and expand YOLO railway defect dataset.
Combines multiple sources with intelligent augmentation and label synchronization.
"""
import os
import sys
import json
import shutil
import random
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import cv2
from tqdm import tqdm
import yaml

try:
    import albumentations as A
except ImportError:
    A = None

# Ensure project root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# ============================================================================
# Configuration & Class Mapping
# ============================================================================

# Source class name -> YOLO class ID (4 canonical classes)
CLASS_MAPPING = {
    # Railway-specific defects
    'missing_fastener': 0,
    'defective_clip': 1,
    'damaged_fastener': 1,
    'crack': 2,
    'rail_crack': 2,
    'obstruction': 3,
    
    # NEU-DET steel surface defects
    'crazing': 2,          # Maps to crack
    'inclusion': 2,        # Maps to crack
    'patches': 3,          # Maps to obstruction
    'pitted': 2,           # Maps to crack
    'pitted_surface': 2,   # Maps to crack
    'rolled-in_scale': 3,  # Maps to obstruction
    'scratches': 2,        # Maps to crack
    'spalling': 2,         # Maps to crack / surface defect
    'squat': 2,            # Maps to crack / surface defect
    
    # RSDDs rail surface defects
    'Type-I': 2,           # Rolling contact fatigue -> crack
    'Type-II': 2,          # Surface crack -> crack
    'type-i': 2,
    'type-ii': 2,
}

CLASS_NAMES = ['missing_fastener', 'defective_clip', 'crack', 'obstruction']
TARGET_SAMPLES_PER_CLASS = 250
AUGMENTATION_FACTOR = 10


# ============================================================================
# Dataset Loaders & Sanitization
# ============================================================================

def download_kaggle_dataset(dataset_slug: str, output_dir: Path) -> bool:
    """Download dataset from Kaggle if kaggle API is configured."""
    try:
        import kaggle
        output_dir.mkdir(parents=True, exist_ok=True)
        kaggle.api.dataset_download_files(dataset_slug, path=str(output_dir), unzip=True)
        print(f"[INFO] Successfully downloaded {dataset_slug} to {output_dir}")
        return True
    except Exception as e:
        print(f"[WARN] Kaggle download skipped for {dataset_slug}: {e}")
        return False


def sanitize_bbox(bbox: List[float]) -> Optional[List[float]]:
    """Sanitize and clamp YOLO bbox coordinates [x_center, y_center, width, height]."""
    if len(bbox) < 4:
        return None
    
    x, y, w, h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    
    # Reject degenerate or invalid boxes
    if w <= 0.005 or h <= 0.005:
        return None
    
    # Clamp center
    x = max(0.01, min(0.99, x))
    y = max(0.01, min(0.99, y))
    
    # Clamp dimensions
    w = max(0.01, min(1.0, w))
    h = max(0.01, min(1.0, h))
    
    # Ensure box fits in bounds [0, 1]
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



def load_original_railway_dataset(data_root: Path) -> List[Dict]:
    """Load the original railway track fault dataset from train/valid/test splits."""
    samples = []
    
    for split in ['train', 'valid', 'test']:
        img_dir = data_root / split / 'images'
        lbl_dir = data_root / split / 'labels'
        
        if not img_dir.exists():
            continue
        
        for img_path in sorted(list(img_dir.glob('*.jpg')) + list(img_dir.glob('*.png'))):
            lbl_path = lbl_dir / (img_path.stem + '.txt')
            
            bboxes = []
            if lbl_path.exists():
                with open(lbl_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            try:
                                class_id = int(parts[0])
                                raw_box = [float(x) for x in parts[1:5]]
                                clean_box = sanitize_bbox(raw_box)
                                if clean_box is not None and 0 <= class_id < 4:
                                    bboxes.append({'class_id': class_id, 'bbox': clean_box})
                            except (ValueError, IndexError):
                                continue
            
            if bboxes:
                samples.append({
                    'image_path': str(img_path),
                    'bboxes': bboxes,
                    'source': 'original_rail_defects'
                })
    
    return samples


def load_neudet_dataset(neudet_dir: Path) -> List[Dict]:
    """Load NEU-DET steel surface defect dataset."""
    samples = []
    
    if not neudet_dir.exists():
        return samples
    
    images_dir = neudet_dir / 'IMAGES' if (neudet_dir / 'IMAGES').exists() else neudet_dir
    
    for defect_dir in images_dir.iterdir():
        if not defect_dir.is_dir():
            continue
        
        class_name = defect_dir.name.lower().replace(' ', '_').replace('-', '_')
        if class_name not in CLASS_MAPPING:
            continue
        
        class_id = CLASS_MAPPING[class_name]
        
        for img_path in sorted(list(defect_dir.glob('*.jpg')) + list(defect_dir.glob('*.png'))):
            # Center defect region bounding box
            bbox = sanitize_bbox([0.5, 0.5, 0.5, 0.5])
            if bbox:
                samples.append({
                    'image_path': str(img_path),
                    'bboxes': [{'class_id': class_id, 'bbox': bbox}],
                    'source': f'neudet_{class_name}'
                })
    
    return samples


def load_rsdds_dataset(rsdds_dir: Path) -> List[Dict]:
    """Load RSDDs rail surface defect dataset."""
    samples = []
    if not rsdds_dir.exists():
        return samples
    
    for img_path in sorted(list(rsdds_dir.glob('**/*.jpg')) + list(rsdds_dir.glob('**/*.png'))):
        lbl_path = img_path.with_suffix('.txt')
        bboxes = []
        if lbl_path.exists():
            with open(lbl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        try:
                            clean_box = sanitize_bbox([float(x) for x in parts[1:5]])
                            if clean_box:
                                bboxes.append({'class_id': 2, 'bbox': clean_box})  # RSDDs are cracks
                        except Exception:
                            continue
        else:
            clean_box = sanitize_bbox([0.5, 0.5, 0.6, 0.3])
            if clean_box:
                bboxes.append({'class_id': 2, 'bbox': clean_box})
        
        if bboxes:
            samples.append({
                'image_path': str(img_path),
                'bboxes': bboxes,
                'source': 'rsdds'
            })
    return samples


# ============================================================================
# Augmentation Pipeline
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
    """
    Create aggressive augmentation pipeline for railway defect detection.
    Simulates real-world conditions: motion blur, weather, lighting, vibration.
    Compatible across Albumentations versions with pure OpenCV/NumPy fallbacks.
    """
    if A is None:
        return {
            'basic': (_SimpleYoloTransform(_fallback_yolo_basic, uses_bbox=True), True),
            'lighting': (_SimpleYoloTransform(_fallback_yolo_lighting, uses_bbox=False), False),
            'weather': (_SimpleYoloTransform(_fallback_yolo_weather, uses_bbox=False), False),
            'motion': (_SimpleYoloTransform(_fallback_yolo_motion, uses_bbox=False), False),
            'geometric': (_SimpleYoloTransform(_fallback_yolo_geometric, uses_bbox=True), True),
            'occlusion': (_SimpleYoloTransform(_fallback_yolo_occlusion, uses_bbox=False), False),
        }
    
    # Level 1: Basic transforms
    basic_transforms = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.3),
        A.RandomRotate90(p=0.3),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.1))
    
    # Level 2: Lighting and color (simulate different times of day / glare)
    lighting_transforms = A.Compose([
        A.RandomBrightnessContrast(
            brightness_limit=0.35,
            contrast_limit=0.35,
            p=0.7
        ),
        A.HueSaturationValue(
            hue_shift_limit=15,
            sat_shift_limit=25,
            val_shift_limit=20,
            p=0.5
        ),
        A.CLAHE(clip_limit=3.0, tile_grid_size=(8, 8), p=0.3),
    ])
    
    # Level 3: Weather and environmental (simulate rain, fog, dust)
    weather_transforms = A.Compose([
        A.RandomRain(
            slant_range=(-10, 10),
            drop_length=15,
            drop_width=1,
            drop_color=(200, 200, 200),
            blur_value=2,
            brightness_coefficient=0.8,
            p=0.25
        ),
        A.RandomFog(
            alpha_coef=0.08,
            fog_coef_range=(0.1, 0.3),
            p=0.25
        ),
        A.RandomSunFlare(
            flare_roi=(0, 0, 1, 0.5),
            angle_range=(0, 1),
            num_flare_circles_range=(1, 3),
            p=0.15
        ),
    ])
    
    # Level 4: Motion and vibration (simulate high-speed TRC bogie movement)
    motion_transforms = A.Compose([
        A.MotionBlur(blur_limit=7, p=0.4),
        A.GaussianBlur(blur_limit=5, p=0.3),
        A.GaussNoise(p=0.3),
    ])
    
    # Level 5: Geometric transforms (simulate different camera angles & rail perspective)
    geometric_transforms = A.Compose([
        A.Affine(
            scale=(0.85, 1.15),
            translate_percent=(-0.08, 0.08),
            rotate=(-12, 12),
            shear=(-4, 4),
            p=0.5
        ),
        A.Perspective(scale=(0.04, 0.08), p=0.3),
        A.ElasticTransform(
            alpha=1,
            sigma=30,
            p=0.2
        ),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.1))
    
    # Level 6: Occlusion and dropout (simulate dust, ballast debris, sensor dropouts)
    occlusion_transforms = A.Compose([
        A.CoarseDropout(
            num_holes_range=(2, 6),
            hole_height_range=(8, 24),
            hole_width_range=(8, 24),
            fill=0,
            p=0.35
        ),
        A.GridDropout(ratio=0.2, p=0.2),
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
    
    # Randomly select 2-4 augmentation levels
    num_levels = random.randint(2, 4)
    selected_keys = random.sample(list(pipelines.keys()), num_levels)
    
    current_img = image.copy()
    bbox_coords = [b['bbox'] for b in bboxes]
    class_labels = [b['class_id'] for b in bboxes]
    
    for key in selected_keys:
        pipeline, uses_bbox = pipelines[key]
        try:
            if uses_bbox:
                transformed = pipeline(
                    image=current_img,
                    bboxes=bbox_coords,
                    class_labels=class_labels
                )
                if transformed['bboxes'] and len(transformed['bboxes']) == len(class_labels):
                    current_img = transformed['image']
                    bbox_coords = transformed['bboxes']
                    class_labels = transformed['class_labels']
            else:
                transformed = pipeline(image=current_img)
                current_img = transformed['image']
        except Exception:
            continue
    
    # Reconstruct sanitized bboxes
    augmented_bboxes = []
    for cls, raw_box in zip(class_labels, bbox_coords):
        clean_box = sanitize_bbox(raw_box)
        if clean_box is not None:
            augmented_bboxes.append({'class_id': cls, 'bbox': clean_box})
    
    if not augmented_bboxes:
        return current_img, bboxes
    
    return current_img, augmented_bboxes


def save_sample(sample: Dict, output_split_dir: Path, sample_id: int):
    """Save augmented sample to disk."""
    img_name = f"img_{sample_id:06d}.jpg"
    lbl_name = f"img_{sample_id:06d}.txt"
    
    img_dir = output_split_dir / 'images'
    lbl_dir = output_split_dir / 'labels'
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    
    # Save image
    if 'image' in sample:
        cv2.imwrite(str(img_dir / img_name), sample['image'])
    elif 'image_path' in sample and os.path.exists(sample['image_path']):
        shutil.copy(sample['image_path'], img_dir / img_name)
    
    # Save label
    with open(lbl_dir / lbl_name, 'w', encoding='utf-8') as f:
        for bbox in sample.get('bboxes', []):
            class_id = int(bbox['class_id'])
            clean_box = sanitize_bbox(bbox['bbox'])
            if clean_box:
                x, y, w, h = clean_box
                f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")


# ============================================================================
# Main Expansion Logic
# ============================================================================

def expand_dataset(
    original_data_root: Path,
    output_root: Path,
    target_per_class: int = TARGET_SAMPLES_PER_CLASS,
    augment_factor: int = AUGMENTATION_FACTOR,
    random_seed: int = 42,
) -> Dict[str, List[Dict]]:
    """
    Expand dataset by aggregating sources and applying multi-level railway augmentations.
    """
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    print("=" * 70)
    print("TrackChain YOLO Dataset Expansion Pipeline")
    print("=" * 70)
    print(f"Source root:      {original_data_root}")
    print(f"Output root:      {output_root}")
    print(f"Target/class:     {target_per_class}")
    print(f"Augment factor:   {augment_factor}")
    
    # Clean/setup output directories
    output_root.mkdir(parents=True, exist_ok=True)
    for split in ['train', 'valid', 'test']:
        (output_root / split / 'images').mkdir(parents=True, exist_ok=True)
        (output_root / split / 'labels').mkdir(parents=True, exist_ok=True)
    
    # 1. Load original railway dataset
    print("\n[1/5] Loading original railway defect dataset...")
    original_samples = load_original_railway_dataset(original_data_root)
    print(f"      Found {len(original_samples)} annotated railway samples")
    
    # 2. Check auxiliary datasets (NEU-DET, RSDDs)
    print("\n[2/5] Checking auxiliary defect sources (NEU-DET, RSDDs)...")
    parent_data_dir = original_data_root.parent
    neudet_dir = parent_data_dir / 'neudet'
    rsdds_dir = parent_data_dir / 'rsdds'
    
    neudet_samples = load_neudet_dataset(neudet_dir)
    rsdds_samples = load_rsdds_dataset(rsdds_dir)
    print(f"      Found {len(neudet_samples)} NEU-DET samples, {len(rsdds_samples)} RSDDs samples")
    
    all_samples = original_samples + neudet_samples + rsdds_samples
    
    # If no samples at all found, raise error
    if not all_samples:
        raise RuntimeError(f"No samples found in {original_data_root} or auxiliary directories.")
    
    # 3. Analyze class distribution
    class_counts = {i: 0 for i in range(4)}
    for sample in all_samples:
        for bbox in sample['bboxes']:
            cid = bbox['class_id']
            if cid in class_counts:
                class_counts[cid] += 1
    
    print(f"\n[3/5] Base class distribution:")
    for class_id, count in class_counts.items():
        name = CLASS_NAMES[class_id]
        print(f"      Class {class_id} ({name:18s}): {count} base annotations")
    
    # 4. Create augmentation pipelines
    print("\n[4/5] Initializing 6-level railway augmentation pipelines...")
    pipelines = create_railway_augmentation_pipeline()
    
    # 5. Expand & Stratify
    print(f"\n[5/5] Synthesizing & augmenting dataset (target: {target_per_class} per class)...")
    output_samples = {'train': [], 'valid': [], 'test': []}
    global_sample_id = 0
    
    # Process each class separately to ensure balanced representation
    for target_class in range(4):
        class_samples = [
            s for s in all_samples
            if any(b['class_id'] == target_class for b in s['bboxes'])
        ]
        
        if not class_samples:
            print(f"      [WARN] No base samples for Class {target_class} ({CLASS_NAMES[target_class]}). Using general pool.")
            class_samples = all_samples
        
        current_count = class_counts.get(target_class, 0)
        needed = max(target_per_class, current_count * augment_factor)
        samples_per_original = max(1, (needed + len(class_samples) - 1) // len(class_samples))
        
        print(f"      Expanding Class {target_class} ({CLASS_NAMES[target_class]}): {len(class_samples)} source -> {needed} target")
        
        count_for_class = 0
        for sample in tqdm(class_samples, desc=f"Augmenting Class {target_class}"):
            img = cv2.imread(sample['image_path'])
            if img is None:
                continue
            
            sample_bboxes = sample['bboxes']
            
            for aug_idx in range(samples_per_original):
                if aug_idx == 0:
                    aug_img = img.copy()
                    aug_bboxes = sample_bboxes
                else:
                    aug_img, aug_bboxes = augment_sample(img, sample_bboxes, pipelines)
                
                # Deterministic balanced split: 80% train, 15% valid, 5% test
                split_idx = global_sample_id % 20
                if split_idx < 16:
                    split = 'train'
                elif split_idx < 19:
                    split = 'valid'
                else:
                    split = 'test'
                
                saved_sample = {
                    'image': aug_img,
                    'bboxes': aug_bboxes,
                    'source': sample.get('source', 'augmented')
                }
                
                save_sample(saved_sample, output_root / split, global_sample_id)
                output_samples[split].append(saved_sample)
                global_sample_id += 1
                count_for_class += 1
                
                if count_for_class >= needed:
                    break
            
            if count_for_class >= needed:
                break
    
    # 6. Generate data.yaml with clean relative paths
    abs_out = output_root.resolve().as_posix()
    data_yaml = {
        'path': abs_out,
        'train': 'train/images',
        'val': 'valid/images',
        'test': 'test/images',
        'nc': len(CLASS_NAMES),
        'names': CLASS_NAMES
    }
    
    yaml_path = output_root / 'data.yaml'
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data_yaml, f, sort_keys=False)
    
    print("\n" + "=" * 70)
    print("Dataset Expansion Complete!")
    print("=" * 70)
    print(f"Train split: {len(output_samples['train'])} images")
    print(f"Valid split: {len(output_samples['valid'])} images")
    print(f"Test split:  {len(output_samples['test'])} images")
    print(f"Total:       {global_sample_id} images")
    print(f"Data YAML:   {yaml_path}")
    
    return output_samples


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Expand and aggregate TrackChain YOLO railway defect dataset")
    parser.add_argument('--data-root', type=str, default='data/external/rail_defects')
    parser.add_argument('--output-root', type=str, default='data/external/rail_defects_expanded')
    parser.add_argument('--target-per-class', type=int, default=250)
    parser.add_argument('--augment-factor', type=int, default=10)
    parser.add_argument('--seed', type=int, default=42)
    
    args = parser.parse_args()
    
    expand_dataset(
        original_data_root=Path(args.data_root),
        output_root=Path(args.output_root),
        target_per_class=args.target_per_class,
        augment_factor=args.augment_factor,
        random_seed=args.seed
    )
