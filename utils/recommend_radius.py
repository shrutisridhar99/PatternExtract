"""
recommend_radius.py
Computes the cohort-specific nearest-neighbour distance distribution
from coordinate CSV files and recommends an optimal kernel radius.

Usage:
    python utils/recommend_radius.py --csv_dir data/CSV/ --pixel_size 1.033

Arguments:
    --csv_dir     Path to folder containing coordinate CSV files (tab-separated)
    --pixel_size  Pixel size in microns per pixel (default: 1.033 for BCA cohort)
    --x_col       Column name for X coordinates (default: "Centroid X µm")
    --y_col       Column name for Y coordinates (default: "Centroid Y µm")
"""

import argparse
import glob
import os
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

def compute_median_nn(csv_path, x_col, y_col):
    try:
        df = pd.read_csv(csv_path, sep='\t')
        if x_col not in df.columns or y_col not in df.columns:
            return None
        coords = df[[x_col, y_col]].dropna().values
        if len(coords) < 2:
            return None
        tree = cKDTree(coords)
        dists, _ = tree.query(coords, k=2)
        nn_dists = dists[:, 1]  # exclude self
        return np.median(nn_dists)
    except Exception as e:
        print(f"  Warning: could not process {os.path.basename(csv_path)}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Recommend optimal kernel radius for PatternExtract"
    )
    parser.add_argument("--csv_dir",    required=True,
                        help="Path to folder containing coordinate CSV files")
    parser.add_argument("--pixel_size", type=float, default=1.033,
                        help="Pixel size in microns/pixel (default: 1.033)")
    parser.add_argument("--x_col",     default="Centroid X µm",
                        help="Column name for X coordinates")
    parser.add_argument("--y_col",     default="Centroid Y µm",
                        help="Column name for Y coordinates")
    args = parser.parse_args()

    csv_files = glob.glob(os.path.join(args.csv_dir, "*.txt")) + \
                glob.glob(os.path.join(args.csv_dir, "*.csv"))

    if not csv_files:
        print(f"No CSV/TXT files found in {args.csv_dir}")
        return

    print(f"Found {len(csv_files)} files. Computing nearest-neighbour distances...")

    nn_medians = []
    for f in csv_files:
        med = compute_median_nn(f, args.x_col, args.y_col)
        if med is not None:
            nn_medians.append(med)

    if not nn_medians:
        print("Could not compute NN distances from any file. Check column names.")
        return

    nn_array       = np.array(nn_medians)
    cohort_median  = np.median(nn_array)
    cohort_std     = np.std(nn_array)
    recommended_px = int(np.ceil(cohort_median))
    recommended_um = cohort_median * args.pixel_size

    print(f"\n=== PatternExtract Kernel Radius Recommendation ===")
    print(f"Images analysed:              {len(nn_medians)}")
    print(f"Cohort median NN distance:    {cohort_median:.1f} ± {cohort_std:.1f} px")
    print(f"                              {recommended_um:.1f} µm")
    print(f"Recommended kernel radius:    {recommended_px} px")
    print(f"  (= 1 inter-cell spacing, minimum to connect adjacent cells)")
    print(f"\nUsage in PatternExtract:")
    print(f"  Set thickness={recommended_px} in mask_generation.py")
    print(f"  Set radius={recommended_px} in mask_generation.py")
    print(f"====================================================")

if __name__ == "__main__":
    main()