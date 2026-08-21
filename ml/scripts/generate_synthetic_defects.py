"""
TrackChain Master Synthetic Defect Dataset Generator (tc.v1 SOTA).
Generates an annotated YOLO defect dataset using the normal-track image bank as canvas:
  1. Inpainting / empty socket generation for missing fasteners (Class 0)
  2. Deformed, sheared, fractured clip overlays for defective clips (Class 1)
  3. Branching / rolling-contact fatigue fissure synthesis for cracks (Class 2)
  4. Ballast / trackbed foreign object placement for obstructions (Class 3)
  5. Multi-defect synthesis and optional SAHI overlapping tiling for small-object sensitivity.
"""

import argparse
import os
import sys
import shutil
import random
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

from ml.data.synthetic_vision import (
    SyntheticRailDefectGenerator,
    sanitize_bbox,
    CLASS_MAPPING,
    CLASS_NAMES,
)
from ml.scripts.expand_datasets import generate_track_pattern


def create_procedural_normal_canvas(width: int = 960, height: int = 960) -> np.ndarray:
    """Generate a high-resolution base normal track canvas."""
    return generate_track_pattern(width=width, height=height)


def load_normal_bank_images(normal_bank_dir: Path) -> List[Path]:
    """Collect all available normal track images from normal bank directory."""
    if not normal_bank_dir.exists():
        return []
    exts = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
    images = []
    for ext in exts:
        images.extend(normal_bank_dir.glob(f"**/{ext}"))
    return images


def slice_image_and_boxes(
    image: np.ndarray,
    boxes: List[Dict[str, Any]],
    slice_size: int = 640,
    overlap_ratio: float = 0.2,
    min_visibility: float = 0.3,
) -> List[Tuple[np.ndarray, List[Dict[str, Any]]]]:
    """
    Slice a high-resolution image into overlapping tiles and recalculate
    YOLO normalized bounding boxes for each tile.
    """
    h, w = image.shape[:2]
    step = int(slice_size * (1.0 - overlap_ratio))
    results = []

    # If image is smaller than or equal to slice_size, return original
    if h <= slice_size and w <= slice_size:
        return [(image, boxes)]

    y_starts = list(range(0, max(1, h - slice_size + 1), step))
    if y_starts[-1] + slice_size < h:
        y_starts.append(h - slice_size)

    x_starts = list(range(0, max(1, w - slice_size + 1), step))
    if x_starts[-1] + slice_size < w:
        x_starts.append(w - slice_size)

    for y in y_starts:
        for x in x_starts:
            tile = image[y : y + slice_size, x : x + slice_size]
            tile_boxes = []

            for b in boxes:
                cls_id = b["class_id"]
                bx, by, bw, bh = b["bbox"]

                # Convert normalized global box to pixel coordinates
                gx1 = (bx - bw / 2.0) * w
                gy1 = (by - bh / 2.0) * h
                gx2 = (bx + bw / 2.0) * w
                gy2 = (by + bh / 2.0) * h
                orig_area = max(1e-5, (gx2 - gx1) * (gy2 - gy1))

                # Intersect with current tile [x, y, x + slice_size, y + slice_size]
                ix1 = max(float(x), gx1)
                iy1 = max(float(y), gy1)
                ix2 = min(float(x + slice_size), gx2)
                iy2 = min(float(y + slice_size), gy2)

                if ix2 > ix1 and iy2 > iy1:
                    inter_area = (ix2 - ix1) * (iy2 - iy1)
                    if inter_area / orig_area >= min_visibility:
                        # Local tile pixel coordinates
                        lx1 = ix1 - x
                        ly1 = iy1 - y
                        lx2 = ix2 - x
                        ly2 = iy2 - y

                        # Normalize to tile dimensions
                        tc_x = (lx1 + lx2) / (2.0 * slice_size)
                        tc_y = (ly1 + ly2) / (2.0 * slice_size)
                        tc_w = (lx2 - lx1) / float(slice_size)
                        tc_h = (ly2 - ly1) / float(slice_size)

                        clean = sanitize_bbox([tc_x, tc_y, tc_w, tc_h])
                        if clean:
                            tile_boxes.append({"class_id": cls_id, "bbox": clean})

            if tile_boxes:  # Only retain tiles containing defect annotations
                results.append((tile, tile_boxes))

    return results


def generate_synthetic_dataset(
    normal_bank_dir: str = "data/external/rail_normal_only",
    output_dir: str = "data/external/rail_defects_synthetic",
    samples_per_class: int = 300,
    multi_defect_ratio: float = 0.35,
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    img_size: int = 960,
    sahi_slice: bool = False,
    slice_size: int = 640,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Generate comprehensive synthetic defect dataset ready for YOLO training.
    """
    random.seed(seed)
    np.random.seed(seed)

    abs_normal = Path(normal_bank_dir) if Path(normal_bank_dir).is_absolute() else repo_root / normal_bank_dir
    abs_output = Path(output_dir) if Path(output_dir).is_absolute() else repo_root / output_dir
    abs_output.mkdir(parents=True, exist_ok=True)

    for split in ["train", "valid", "test"]:
        (abs_output / split / "images").mkdir(parents=True, exist_ok=True)
        (abs_output / split / "labels").mkdir(parents=True, exist_ok=True)

    normal_images = load_normal_bank_images(abs_normal)
    print("=" * 75)
    print("TrackChain Synthetic Defect Dataset Synthesis (tc.v1 SOTA)")
    print("=" * 75)
    print(f"Normal Bank:         {abs_normal} (Found {len(normal_images)} images)")
    print(f"Output Directory:    {abs_output}")
    print(f"Target Per Class:    {samples_per_class} defect instances")
    print(f"Multi-Defect Ratio:  {multi_defect_ratio:.1%}")
    print(f"Base Image Size:     {img_size}x{img_size}")
    print(f"SAHI Tiling:         {sahi_slice} (Slice size={slice_size})")

    generator = SyntheticRailDefectGenerator(random_seed=seed)
    raw_samples: List[Dict[str, Any]] = []

    # Defect instance tracking
    counts = {c: 0 for c in CLASS_NAMES}
    total_target = samples_per_class * len(CLASS_NAMES)
    pbar = tqdm(total=total_target, desc="Synthesizing Defect Samples")

    sample_counter = 0

    while min(counts.values()) < samples_per_class:
        # Obtain base image
        if normal_images:
            chosen_path = random.choice(normal_images)
            base_img = cv2.imread(str(chosen_path))
            if base_img is None:
                base_img = create_procedural_normal_canvas(width=img_size, height=img_size)
            else:
                base_img = cv2.resize(base_img, (img_size, img_size))
        else:
            base_img = create_procedural_normal_canvas(width=img_size, height=img_size)

        # Decide which defects to inject
        needed_classes = [c for c, cnt in counts.items() if cnt < samples_per_class]
        if not needed_classes:
            break

        primary_class = random.choice(needed_classes)
        chosen_types = [primary_class]

        if random.random() < multi_defect_ratio:
            secondary_class = random.choice(CLASS_NAMES)
            chosen_types.append(secondary_class)

        syn_img, bboxes = generator.generate_synthetic_sample(base_img, defect_types=chosen_types)

        if bboxes:
            sample_counter += 1
            for b in bboxes:
                c_name = CLASS_NAMES[b["class_id"]]
                counts[c_name] += 1
                pbar.update(1)

            if sahi_slice:
                # Apply SAHI slicing
                sliced = slice_image_and_boxes(syn_img, bboxes, slice_size=slice_size)
                for s_img, s_boxes in sliced:
                    raw_samples.append({"image": s_img, "bboxes": s_boxes})
            else:
                raw_samples.append({"image": syn_img, "bboxes": bboxes})

    pbar.close()

    # Shuffle and split into train, valid, test
    random.shuffle(raw_samples)
    total_samples = len(raw_samples)
    n_train = int(total_samples * train_ratio)
    n_val = int(total_samples * val_ratio)

    splits = {
        "train": raw_samples[:n_train],
        "valid": raw_samples[n_train : n_train + n_val],
        "test": raw_samples[n_train + n_val :],
    }

    # Write files to disk
    idx = 0
    split_counts = {"train": 0, "valid": 0, "test": 0}
    for split_name, split_list in splits.items():
        img_dir = abs_output / split_name / "images"
        lbl_dir = abs_output / split_name / "labels"
        split_counts[split_name] = len(split_list)

        for item in split_list:
            idx += 1
            img_file = img_dir / f"syn_{idx:06d}.jpg"
            lbl_file = lbl_dir / f"syn_{idx:06d}.txt"

            cv2.imwrite(str(img_file), item["image"])
            with open(lbl_file, "w", encoding="utf-8") as f:
                for b in item["bboxes"]:
                    box = b["bbox"]
                    f.write(f"{b['class_id']} {box[0]:.6f} {box[1]:.6f} {box[2]:.6f} {box[3]:.6f}\n")

    # Generate data.yaml
    data_yaml = {
        "path": abs_output.resolve().as_posix(),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": 4,
        "names": CLASS_NAMES,
    }

    data_yaml_path = abs_output / "data.yaml"
    with open(data_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, sort_keys=False)

    print("\n" + "=" * 75)
    print("Synthetic Defect Dataset Generation Completed")
    print("=" * 75)
    print(f"Total Images Generated: {total_samples}")
    print(f"  - Train Split:        {split_counts['train']}")
    print(f"  - Valid Split:        {split_counts['valid']}")
    print(f"  - Test Split:         {split_counts['test']}")
    print("-" * 75)
    print("Defect Instances Synthesized:")
    for c_name, c_count in counts.items():
        print(f"  - {c_name:20s}: {c_count}")
    print(f"Dataset YAML:           {data_yaml_path}")
    print("=" * 75)

    return {
        "total_images": total_samples,
        "splits": split_counts,
        "class_counts": counts,
        "data_yaml": str(data_yaml_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic railway defect YOLO dataset.")
    parser.add_argument("--normal-bank", default="data/external/rail_normal_only", help="Path to normal track images")
    parser.add_argument("--output-dir", default="data/external/rail_defects_synthetic", help="Output directory")
    parser.add_argument("--samples-per-class", type=int, default=300, help="Target defect count per class")
    parser.add_argument("--multi-defect-ratio", type=float, default=0.35, help="Ratio of multi-defect images")
    parser.add_argument("--imgsz", type=int, default=960, help="Base image resolution")
    parser.add_argument("--sahi-slice", action="store_true", help="Apply SAHI overlapping slicing")
    parser.add_argument("--slice-size", type=int, default=640, help="SAHI tile slice size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    generate_synthetic_dataset(
        normal_bank_dir=args.normal_bank,
        output_dir=args.output_dir,
        samples_per_class=args.samples_per_class,
        multi_defect_ratio=args.multi_defect_ratio,
        img_size=args.imgsz,
        sahi_slice=args.sahi_slice,
        slice_size=args.slice_size,
        seed=args.seed,
    )
