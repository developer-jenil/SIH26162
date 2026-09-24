"""Materialise schema-valid training dataset for AGNIVANI."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import pandas as pd

from agnivani.features.build import FEATURES, build_features, spatial_block_id
from agnivani.geo.registry import load_facilities
from agnivani.models.scorer import CLASSES


def materialise(data_dir: Path | str = Path("data"), include_synthetic: bool = False) -> pd.DataFrame:
    data_dir = Path(data_dir)
    proc_dir = data_dir / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)

    labelled_path = proc_dir / "labelled.parquet"
    if not labelled_path.exists():
        raise FileNotFoundError(f"labelled.parquet not found in '{proc_dir}'")

    raw_df = pd.read_parquet(labelled_path)
    sources_df = raw_df.copy()

    if include_synthetic:
        synth_path = proc_dir / "synthetic_blobs.parquet"
        if synth_path.exists():
            synth_df = pd.read_parquet(synth_path)
            sources_df = pd.concat([sources_df, synth_df], ignore_index=True)

    # Filter out UNLABELLED rows if present so dataset has ground-truth classes
    if "label" in sources_df.columns:
        valid_mask = sources_df["label"].isin(CLASSES)
        sources_df = sources_df[valid_mask].copy()

    # Load facilities
    facs = load_facilities(data_dir)

    # Run feature construction
    feats = build_features(sources_df, facs)

    # Merge features with original raw columns
    merged = feats.copy()
    for col in sources_df.columns:
        if col not in merged.columns:
            merged[col] = sources_df[col].values

    # Set cls column
    if "label" in sources_df.columns:
        merged["cls"] = sources_df["label"].values
    elif "cls" in sources_df.columns:
        merged["cls"] = sources_df["cls"].values
    else:
        raise ValueError("Neither 'label' nor 'cls' column found in dataset")

    # Ensure block_id is present
    if "block_id" not in merged.columns or merged["block_id"].isna().any():
        merged["block_id"] = [
            spatial_block_id(float(lat), float(lon))
            for lat, lon in zip(merged["centroid_lat"], merged["centroid_lon"])
        ]

    # Verify column contract
    required = set(FEATURES) | {"cls", "block_id"}
    missing = required - set(merged.columns)
    if missing:
        raise ValueError(f"Materialised training set missing required columns: {sorted(missing)}")

    # Atomic write to labelled.parquet
    tmp_path = proc_dir / "labelled.parquet.tmp"
    target_path = proc_dir / "labelled.parquet"
    merged.to_parquet(tmp_path, index=False)
    if target_path.exists():
        os.replace(tmp_path, target_path)
    else:
        tmp_path.rename(target_path)

    print(f"[ok] Materialised training set saved to {target_path} ({len(merged)} rows, {len(merged.columns)} cols)")
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Materialise training dataset.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Path to data directory")
    parser.add_argument("--include-synthetic", action="store_true", help="Include synthetic blobs in training set")
    args = parser.parse_args()
    materialise(data_dir=args.data_dir, include_synthetic=args.include_synthetic)
