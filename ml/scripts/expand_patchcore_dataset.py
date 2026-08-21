"""
Master script to expand PatchCore normal dataset for railway anomaly detection.
Aggregates multiple sources with intelligent augmentation and diversity sampling.
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
from sklearn.cluster import KMeans

try:
    import albumentations as A
except ImportError:
    A = None

# Ensure project root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# ============================================================================
# Configuration
# ============================================================================

TARGET_NORMAL_SAMPLES = 800
AUGMENTATION_FACTOR = 8
DIVERSITY_CLUSTERS = 30  # For ensuring dataset diversity

# ============================================================================
# Dataset Sources
# ============================================================================

def extract_normal_from_yolo(yolo_data_root: Path) -> List[Path]:
    """
    Extract defect-free images from YOLO dataset.
    Images with empty label files (or missing label files) are considered normal.
    """
    normal_images = []
    
    for split in ['train', 'valid', 'test']:
        img_dir = yolo_data_root / split / 'images'
        lbl_dir = yolo_data_root / split / 'labels'
        
        if not img_dir.exists():
            continue
        
        for img_path in sorted(list(img_dir.glob('*.jpg')) + list(img_dir.glob('*.png'))):
            lbl_path = lbl_dir / (img_path.stem + '.txt')
            
            # Empty label file = no defects = normal image
            if lbl_path.exists():
                if lbl_path.stat().st_size == 0:
                    normal_images.append(img_path)
            else:
                # No label file also indicates normal
                normal_images.append(img_path)
    
    return normal_images


def extract_existing_normals(normal_data_root: Path) -> List[Path]:
    """Extract all existing normal images from rail_normal_only."""
    normal_images = []
    if not normal_data_root.exists():
        return normal_images
    
    for p in sorted(list(normal_data_root.glob('**/*.jpg')) + list(normal_data_root.glob('**/*.png'))):
        if 'good' in p.parts or 'normal' in p.name.lower():
            normal_images.append(p)
    
    return normal_images


def extract_normal_from_neudet(neudet_dir: Path) -> List[Path]:
    """
    Extract normal/clean samples from NEU-DET dataset if present.
    NEU-DET has clean steel surface images.
    """
    normal_images = []
    
    if not neudet_dir.exists():
        return normal_images
    
    for subdir in neudet_dir.rglob('*'):
        if subdir.is_dir():
            name_lower = subdir.name.lower()
            if any(keyword in name_lower for keyword in ['normal', 'clean', 'good', 'defect-free', 'defect_free']):
                normal_images.extend(list(subdir.glob('*.jpg')) + list(subdir.glob('*.png')))
    
    return normal_images


def generate_track_pattern(width: int = 640, height: int = 640) -> np.ndarray:
    """Generate a high-fidelity procedural synthetic normal railway track pattern."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Ballast gravel texture (gray-brown with granular noise)
    ballast_color = np.array([80, 75, 65], dtype=np.float32)
    noise = np.random.normal(0, 18, (height, width, 3))
    base_ballast = np.clip(ballast_color + noise, 0, 255).astype(np.uint8)
    img[:] = base_ballast
    
    # Sleepers (horizontal wooden/concrete ties)
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
        # Sleeper texture lines
        cv2.line(img, (int(width * 0.15), y + 4), (int(width * 0.85), y + 4), (sleeper_color[0]+15, sleeper_color[1]+15, sleeper_color[2]+15), 1)

    # Two parallel steel rail lines
    rail_width = 24
    rail_spacing = int(width * 0.35)
    center_x = width // 2
    
    for offset in [center_x - rail_spacing // 2, center_x + rail_spacing // 2]:
        # Rail flange and body
        cv2.rectangle(img, (offset - rail_width // 2, 0), (offset + rail_width // 2, height), (50, 50, 55), -1)
        # Shiny rail head reflection
        cv2.line(img, (offset - rail_width // 6, 0), (offset - rail_width // 6, height), (130, 130, 140), 3)
        cv2.line(img, (offset + rail_width // 6, 0), (offset + rail_width // 6, height), (85, 85, 95), 2)
        
        # Fastener clips at each sleeper intersection
        for y in range(10, height, sleeper_spacing):
            clip_y = y + sleeper_height // 2
            # Left clip
            cv2.circle(img, (offset - rail_width // 2 - 6, clip_y), 5, (40, 40, 45), -1)
            # Right clip
            cv2.circle(img, (offset + rail_width // 2 + 6, clip_y), 5, (40, 40, 45), -1)

    return img


def add_realistic_variations(img: np.ndarray) -> np.ndarray:
    """Add realistic lighting and texture variations to synthetic track."""
    if A is None:
        return img
    
    transforms = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.8),
        A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20, val_shift_limit=20, p=0.5),
        A.GaussianBlur(blur_limit=3, p=0.2),
    ])
    
    try:
        return transforms(image=img)['image']
    except Exception:
        return img


def generate_synthetic_normal(output_dir: Path, count: int = 100) -> List[Path]:
    """Generate synthetic normal track images using procedural generation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    synthetic_images = []
    
    print(f"Generating {count} synthetic normal track images...")
    
    for i in tqdm(range(count), desc="Generating synthetic normals"):
        # Create base track pattern
        img = generate_track_pattern()
        # Add realistic variations
        img = add_realistic_variations(img)
        
        img_path = output_dir / f"synthetic_normal_{i:04d}.jpg"
        cv2.imwrite(str(img_path), img)
        synthetic_images.append(img_path)
    
    return synthetic_images

# ============================================================================
# Augmentation Pipeline
# ============================================================================

def create_normal_augmentation_pipeline():
    """
    Create augmentation pipeline for normal track images.
    Focuses on realistic variations without introducing defects.
    Compatible across Albumentations versions.
    """
    if A is None:
        return {}
    
    # Lighting variations (different times of day)
    lighting = A.Compose([
        A.RandomBrightnessContrast(
            brightness_limit=0.35,
            contrast_limit=0.35,
            p=0.7
        ),
        A.CLAHE(clip_limit=3.0, tile_grid_size=(8, 8), p=0.3),
        A.RandomGamma(gamma_limit=(80, 120), p=0.3),
    ])
    
    # Weather effects
    weather_list = [
        A.RandomRain(
            slant_range=(-10, 10),
            drop_length=15,
            drop_width=1,
            drop_color=(180, 180, 180),
            blur_value=2,
            brightness_coefficient=0.8,
            p=0.20
        ),
    ]
    try:
        weather_list.append(A.RandomFog(fog_coef_range=(0.05, 0.2), alpha_coef=0.05, p=0.20))
    except Exception:
        pass
    weather = A.Compose(weather_list)
    
    # Geometric variations (camera angle & track curvature)
    geometric = A.Compose([
        A.Affine(
            scale=(0.92, 1.08),
            translate_percent=(-0.05, 0.05),
            rotate=(-5, 5),
            shear=(-2, 2),
            p=0.5
        ),
        A.Perspective(scale=(0.02, 0.05), p=0.2),
        A.HorizontalFlip(p=0.5),
    ])
    
    # Texture variations (different track conditions)
    texture = A.Compose([
        A.GaussianBlur(blur_limit=3, p=0.3),
        A.MotionBlur(blur_limit=5, p=0.2),
        A.MedianBlur(blur_limit=3, p=0.2),
    ])
    
    # Color variations (different materials, aging)
    color = A.Compose([
        A.HueSaturationValue(
            hue_shift_limit=15,
            sat_shift_limit=25,
            val_shift_limit=25,
            p=0.5
        ),
        A.ToGray(p=0.05),
    ])
    
    return {
        'lighting': lighting,
        'weather': weather,
        'geometric': geometric,
        'texture': texture,
        'color': color,
    }


def augment_normal_image(image: np.ndarray, pipelines: Dict, num_augmentations: int = 5) -> List[np.ndarray]:
    """Generate multiple augmented versions of a normal image."""
    augmented = [image]  # Include original
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

# ============================================================================
# Diversity Sampling
# ============================================================================

def ensure_diversity(images: List[Path], target_count: int, num_clusters: int = DIVERSITY_CLUSTERS) -> List[Path]:
    """
    Use clustering to ensure dataset diversity.
    Samples from different clusters to avoid redundancy.
    """
    if len(images) <= target_count:
        return images
    
    print(f"Ensuring diversity: selecting {target_count} from {len(images)} images using {num_clusters} clusters...")
    
    features = []
    valid_images = []
    
    for img_path in tqdm(images, desc="Extracting features for diversity"):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        
        # Resize for speed
        img_small = cv2.resize(img, (64, 64))
        
        # Features: mean color per channel + std + texture energy
        feat = np.concatenate([
            img_small.mean(axis=(0, 1)),
            img_small.std(axis=(0, 1)),
            [float(cv2.Laplacian(cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())]
        ])
        
        features.append(feat)
        valid_images.append(img_path)
    
    if not features:
        return images[:target_count]
    
    features = np.array(features)
    
    # Cluster
    k = min(num_clusters, len(features))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(features)
    
    # Sample proportionally from each cluster
    selected = []
    samples_per_cluster = max(1, target_count // k)
    
    for cluster_id in range(k):
        cluster_indices = np.where(clusters == cluster_id)[0]
        if len(cluster_indices) == 0:
            continue
        
        n_samples = min(samples_per_cluster, len(cluster_indices))
        sampled = random.sample(list(cluster_indices), n_samples)
        selected.extend([valid_images[i] for i in sampled])
    
    # Fill remainder if needed
    if len(selected) < target_count:
        remaining = [img for img in valid_images if img not in selected]
        needed = target_count - len(selected)
        selected.extend(random.sample(remaining, min(needed, len(remaining))))
    
    return selected[:target_count]

# ============================================================================
# Main Expansion Logic
# ============================================================================

def expand_patchcore_dataset(
    yolo_data_root: Path,
    output_root: Path,
    target_count: int = TARGET_NORMAL_SAMPLES,
    augment_factor: int = AUGMENTATION_FACTOR
):
    """
    Expand PatchCore normal dataset with diversity and augmentation.
    """
    print("=" * 70)
    print("TrackChain PatchCore Dataset Expansion Pipeline")
    print("=" * 70)
    
    # Setup output directories
    for split in ['train', 'valid', 'test']:
        (output_root / split / 'good').mkdir(parents=True, exist_ok=True)
    
    # Collect normal images from all sources
    print("\n[1/6] Collecting normal images from multiple sources...")
    
    all_normal_images = []
    
    # Source 1: Existing rail_normal_only
    normal_only_dir = yolo_data_root.parent / 'rail_normal_only'
    if normal_only_dir.exists():
        print("  - Extracting from existing rail_normal_only dataset...")
        existing_normals = extract_existing_normals(normal_only_dir)
        print(f"    Found {len(existing_normals)} existing normal images")
        all_normal_images.extend(existing_normals)
    
    # Source 2: YOLO dataset (defect-free images)
    print("  - Extracting from YOLO dataset...")
    yolo_normals = extract_normal_from_yolo(yolo_data_root)
    print(f"    Found {len(yolo_normals)} normal images")
    all_normal_images.extend(yolo_normals)
    
    # Source 3: NEU-DET (clean steel samples)
    neudet_dir = yolo_data_root.parent / 'neudet'
    if neudet_dir.exists():
        print("  - Extracting from NEU-DET dataset...")
        neudet_normals = extract_normal_from_neudet(neudet_dir)
        print(f"    Found {len(neudet_normals)} normal images")
        all_normal_images.extend(neudet_normals)
    
    # Source 4: Synthetic generation
    print("  - Generating synthetic normal images...")
    synthetic_dir = output_root / 'synthetic'
    synthetic_normals = generate_synthetic_normal(synthetic_dir, count=100)
    print(f"    Generated {len(synthetic_normals)} synthetic images")
    all_normal_images.extend(synthetic_normals)
    
    # Remove duplicates
    all_normal_images = list(dict.fromkeys(all_normal_images))
    print(f"\n  Total unique normal images collected: {len(all_normal_images)}")
    
    # Ensure diversity
    print("\n[2/6] Ensuring dataset diversity...")
    sample_budget = max(50, target_count // augment_factor)
    diverse_images = ensure_diversity(all_normal_images, sample_budget)
    print(f"  Selected {len(diverse_images)} diverse seed images")
    
    # Create augmentation pipeline
    print("\n[3/6] Creating augmentation pipeline...")
    pipelines = create_normal_augmentation_pipeline()
    
    # Augment and save
    print(f"\n[4/6] Augmenting dataset (target: {target_count} samples)...")
    
    output_samples = {'train': [], 'valid': [], 'test': []}
    global_sample_id = 0
    
    for img_path in tqdm(diverse_images, desc="Augmenting normal images"):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        
        # Generate augmented versions
        augmented = augment_normal_image(img, pipelines, num_augmentations=augment_factor)
        
        for aug_img in augmented:
            # Determine split (80% train, 15% valid, 5% test)
            split_rand = random.random()
            if split_rand < 0.80:
                split = 'train'
            elif split_rand < 0.95:
                split = 'valid'
            else:
                split = 'test'
            
            # Save
            img_name = f"normal_{global_sample_id:05d}.jpg"
            img_save_path = output_root / split / 'good' / img_name
            cv2.imwrite(str(img_save_path), aug_img)
            
            output_samples[split].append(img_save_path)
            global_sample_id += 1
            
            if global_sample_id >= target_count:
                break
        
        if global_sample_id >= target_count:
            break
    
    # Create defect samples for validation (for FPR/FNR measurement)
    print("\n[5/6] Creating defect samples for validation...")
    create_defect_validation_set(yolo_data_root, output_root, count=50)
    
    # Generate dataset config
    print("\n[6/6] Generating dataset configuration...")
    dataset_config = {
        'path': str(output_root.absolute()),
        'train': 'train/good',
        'valid': 'valid/good',
        'test': 'test/good',
        'defect_valid': 'valid/defect',
        'normal_count': {
            'train': len(output_samples['train']),
            'valid': len(output_samples['valid']),
            'test': len(output_samples['test'])
        },
        'augmentation_factor': augment_factor,
        'diversity_clusters': DIVERSITY_CLUSTERS
    }
    
    config_path = output_root / 'dataset_config.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(dataset_config, f, default_flow_style=False)
    
    # Print summary
    print("\n" + "=" * 70)
    print("PatchCore Dataset Expansion Complete!")
    print("=" * 70)
    print(f"Normal samples:")
    print(f"  Train: {len(output_samples['train'])} images")
    print(f"  Valid: {len(output_samples['valid'])} images")
    print(f"  Test:  {len(output_samples['test'])} images")
    print(f"\nDefect samples (for validation):")
    defect_valid = output_root / 'valid' / 'defect'
    if defect_valid.exists():
        print(f"  Valid: {len(list(defect_valid.glob('*.jpg')))} images")
    print(f"\nDataset config: {config_path}")
    
    return output_samples


def create_defect_validation_set(yolo_data_root: Path, output_root: Path, count: int = 50):
    """Create defect samples for validation (to measure false negative rate)."""
    defect_dir = output_root / 'valid' / 'defect'
    defect_dir.mkdir(parents=True, exist_ok=True)
    
    defect_images = []
    for split in ['train', 'valid', 'test']:
        lbl_dir = yolo_data_root / split / 'labels'
        img_dir = yolo_data_root / split / 'images'
        
        if not lbl_dir.exists():
            continue
        
        for lbl_path in sorted(list(lbl_dir.glob('*.txt'))):
            if lbl_path.stat().st_size > 0:  # Has defects
                img_path = img_dir / (lbl_path.stem + '.jpg')
                if not img_path.exists():
                    img_path = img_dir / (lbl_path.stem + '.png')
                if img_path.exists():
                    defect_images.append(img_path)
    
    if not defect_images:
        return
    
    selected = random.sample(defect_images, min(count, len(defect_images)))
    
    for i, img_path in enumerate(selected):
        dest_path = defect_dir / f"defect_{i:04d}.jpg"
        shutil.copy(img_path, dest_path)


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Expand PatchCore normal dataset")
    parser.add_argument('--yolo-data', type=str, default='data/external/rail_defects_expanded')
    parser.add_argument('--output', type=str, default='data/external/rail_normal_expanded')
    parser.add_argument('--target-count', type=int, default=800)
    parser.add_argument('--augment-factor', type=int, default=8)
    
    args = parser.parse_args()
    
    expand_patchcore_dataset(
        yolo_data_root=Path(args.yolo_data),
        output_root=Path(args.output),
        target_count=args.target_count,
        augment_factor=args.augment_factor
    )
