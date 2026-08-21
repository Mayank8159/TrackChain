"""
TrackChain Dataset Expansion - YOLO Defect Detection (Consolidated).
Redirects to unified dataset expansion module: ml.scripts.expand_datasets.
"""

from ml.scripts.expand_datasets import (
    sanitize_bbox,
    create_railway_augmentation_pipeline,
    augment_sample,
    expand_dataset,
    CLASS_MAPPING,
    CLASS_NAMES,
)

if __name__ == "__main__":
    from ml.scripts.expand_datasets import expand_dataset
    import argparse
    parser = argparse.ArgumentParser(description="Expand YOLO defect dataset.")
    parser.add_argument("--data-root", default="data/external/rail_defects", help="Original data root")
    parser.add_argument("--output-root", default="data/external/rail_defects_expanded", help="Output directory")
    args = parser.parse_args()
    expand_dataset(data_root=args.data_root, output_root=args.output_root)
