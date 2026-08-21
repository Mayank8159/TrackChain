"""
TrackChain Dataset Expansion - PatchCore Normal Surface Anomaly (Consolidated).
Redirects to unified dataset expansion module: ml.scripts.expand_datasets.
"""

from ml.scripts.expand_datasets import (
    generate_track_pattern,
    create_normal_augmentation_pipeline,
    augment_normal_image,
    ensure_diversity,
    expand_patchcore_dataset,
)

if __name__ == "__main__":
    from ml.scripts.expand_datasets import expand_patchcore_dataset
    import argparse
    parser = argparse.ArgumentParser(description="Expand PatchCore normal track dataset.")
    parser.add_argument("--yolo-data", default="data/external/rail_defects", help="Original data root")
    parser.add_argument("--output", default="data/external/rail_normal_expanded", help="Output directory")
    args = parser.parse_args()
    expand_patchcore_dataset(normal_data_root=args.yolo_data, output_root=args.output)
