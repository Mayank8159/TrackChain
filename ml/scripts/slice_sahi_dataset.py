"""
TrackChain SAHI Dataset Slicer (tc.v1 SOTA).
Slices high-resolution or standard railway defect imagery into overlapping crops,
recomputing normalized YOLO bounding boxes for each tile.
Acts as a dataset multiplier and small-object detection booster (fasteners, clips, micro-cracks).
"""

import argparse
import os
import sys
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

from ml.data.synthetic_vision import sanitize_bbox, CLASS_NAMES
from ml.scripts.generate_synthetic_defects import slice_image_and_boxes


def slice_yolo_dataset(
    input_dir: str = "data/external/rail_defects",
    output_dir: str = "data/external/rail_defects_sahi_sliced",
    slice_size: int = 480,
    overlap_ratio: float = 0.20,
    min_visibility: float = 0.25,
) -> Dict[str, Any]:
    """
    Load an existing YOLO dataset, slice each image into overlapping tiles,
    update bounding boxes, and save to output_dir.
    """
    abs_input = Path(input_dir) if Path(input_dir).is_absolute() else repo_root / input_dir
    abs_output = Path(output_dir) if Path(output_dir).is_absolute() else repo_root / output_dir
    abs_output.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("TrackChain SAHI Dataset Multiplier & Slicer (tc.v1 SOTA)")
    print("=" * 75)
    print(f"Input Dataset:   {abs_input}")
    print(f"Output Dataset:  {abs_output}")
    print(f"Slice Tile Size: {slice_size}x{slice_size}")
    print(f"Overlap Ratio:   {overlap_ratio:.1%}")
    print(f"Min Visibility:  {min_visibility:.1%}")

    stats = {"original_images": 0, "sliced_tiles": 0, "splits": {}}

    for split in ["train", "valid", "test"]:
        in_img_dir = abs_input / split / "images"
        in_lbl_dir = abs_input / split / "labels"
        out_img_dir = abs_output / split / "images"
        out_lbl_dir = abs_output / split / "labels"

        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        if not in_img_dir.exists():
            continue

        img_files = sorted(list(in_img_dir.glob("*.jpg")) + list(in_img_dir.glob("*.png")) + list(in_img_dir.glob("*.jpeg")))
        tile_count = 0

        for img_p in tqdm(img_files, desc=f"Slicing {split} split"):
            stats["original_images"] += 1
            lbl_p = in_lbl_dir / (img_p.stem + ".txt")

            boxes: List[Dict[str, Any]] = []
            if lbl_p.exists():
                with open(lbl_p, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            cls_id = int(parts[0])
                            clean_b = sanitize_bbox([float(x) for x in parts[1:5]])
                            if clean_b:
                                boxes.append({"class_id": cls_id, "bbox": clean_b})

            img = cv2.imread(str(img_p))
            if img is None:
                continue

            sliced_items = slice_image_and_boxes(
                img,
                boxes,
                slice_size=slice_size,
                overlap_ratio=overlap_ratio,
                min_visibility=min_visibility,
            )

            for t_idx, (t_img, t_boxes) in enumerate(sliced_items):
                tile_count += 1
                base_name = f"{img_p.stem}_sahi_{t_idx:02d}"
                out_img_path = out_img_dir / f"{base_name}.jpg"
                out_lbl_path = out_lbl_dir / f"{base_name}.txt"

                cv2.imwrite(str(out_img_path), t_img)
                with open(out_lbl_path, "w", encoding="utf-8") as f:
                    for b in t_boxes:
                        bx = b["bbox"]
                        f.write(f"{b['class_id']} {bx[0]:.6f} {bx[1]:.6f} {bx[2]:.6f} {bx[3]:.6f}\n")

        stats["splits"][split] = tile_count
        stats["sliced_tiles"] += tile_count

    # Generate data.yaml
    data_yaml = {
        "path": abs_output.resolve().as_posix(),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": 4,
        "names": CLASS_NAMES,
    }

    yaml_path = abs_output / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, sort_keys=False)

    print("\n" + "=" * 75)
    print("SAHI Slicing Complete")
    print("=" * 75)
    print(f"Original Images:     {stats['original_images']}")
    print(f"Total Sliced Tiles:  {stats['sliced_tiles']}")
    for sp, cnt in stats["splits"].items():
        print(f"  - {sp:10s}: {cnt} tiles")
    print(f"Dataset YAML:        {yaml_path}")
    print("=" * 75)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slice YOLO dataset using SAHI overlapping tiling.")
    parser.add_argument("--input-dir", default="data/external/rail_defects", help="Source YOLO dataset directory")
    parser.add_argument("--output-dir", default="data/external/rail_defects_sahi_sliced", help="Output sliced directory")
    parser.add_argument("--slice-size", type=int, default=480, help="Tile slice size in pixels")
    parser.add_argument("--overlap-ratio", type=float, default=0.20, help="Tile overlap fraction")
    args = parser.parse_args()

    slice_yolo_dataset(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        slice_size=args.slice_size,
        overlap_ratio=args.overlap_ratio,
    )
