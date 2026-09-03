"""Industrial facility seed registry, labelling, and negative-control sampling.

Extends the facility seed with:
  1. ``label_sources()`` – assigns each VIIRS persistent-source cluster a
     weak ground-truth class label based on nearest-facility proximity and
     landcover.
  2. ``sample_negative_controls()`` – generates hard-negative points (8–25 km
     from every FLARE-labelled cluster) for use in model training.

Label rules (weak labels — admitted as weak):
  - FLARE      (high confidence)  : nearest facility is REFI_GAS or FERTILIZER
                                    within 2000 m
  - IND_FIRE   (medium confidence): nearest facility is STEEL or POWER
                                    within 2000 m
  - COAL       (medium confidence): nearest facility is COAL or CEMENT
                                    within 2000 m
  - WILD       (high confidence) : > 5000 m from ANY facility AND landcover
                                    in {forest, grassland, shrub}
  - UNLABELLED (none)            : otherwise
"""
from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import geopandas as gpd


# ---------------------------------------------------------------------------
# Original seed registry (preserved from previous version)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Facility:
    facility_id: str; name: str; lat: float; lon: float; sector: str
    district: str = ""; state: str = ""; source_of_truth: str = "MANUAL"


_NAMES = [
("Jamnagar Refinery",22.35,70.02,"REFI_GAS"),("Vadinar Refinery",22.56,69.73,"REFI_GAS"),("Kandla Port",23.,70.22,"OTHER"),
("Hazira LNG/Steel",21.13,72.64,"REFI_GAS"),("Dahej LNG",21.71,72.58,"REFI_GAS"),("Mumbai High/Uran",18.88,72.95,"REFI_GAS"),
("Panipat Refinery",29.39,76.97,"REFI_GAS"),("Mathura Refinery",27.59,77.68,"REFI_GAS"),("Bathinda Refinery",30.21,75.,"REFI_GAS"),
("Barauni Refinery",25.44,86.05,"REFI_GAS"),("Bongaigaon Refinery",26.48,90.56,"REFI_GAS"),("Numaligarh Refinery",26.60,93.78,"REFI_GAS"),
("Guwahati Refinery",26.18,91.75,"REFI_GAS"),("Digboi Oil Field",27.39,95.62,"REFI_GAS"),("Duliajan Oil Field",27.36,95.32,"REFI_GAS"),
("Naharkatiya Field",27.28,95.38,"REFI_GAS"),("Bokaro Steel",23.67,86.15,"STEEL"),("Jharia Coalfield",23.75,86.42,"COAL"),
("Jamshedpur Steel",22.80,86.20,"STEEL"),("Rourkela Steel",22.25,84.88,"STEEL"),("Bhilai Steel",21.19,81.35,"STEEL"),
("Korba Thermal",22.36,82.68,"POWER"),("Singrauli Coal",24.20,82.67,"COAL"),("Vindhyachal Thermal",24.09,82.67,"POWER"),
("Talcher Coalfield",20.95,85.23,"COAL"),("Paradip Refinery",20.31,86.61,"REFI_GAS"),("Visakhapatnam",17.70,83.20,"OTHER"),
("Ramagundam Thermal",18.76,79.45,"POWER"),("Manali Refinery",13.23,80.33,"REFI_GAS"),("Neyveli Lignite",11.60,79.48,"COAL"),
("Cauvery Basin",10.77,79.84,"REFI_GAS"),("Mangalore Refinery",12.96,74.80,"REFI_GAS"),("Kochi Refinery",10.,76.28,"REFI_GAS"),
("Tuticorin Thermal",8.76,78.13,"POWER"),("Durgapur Steel",23.52,87.31,"STEEL"),("IISCO Burnpur",23.67,86.94,"STEEL"),
("Ankleshwar Ind.",21.63,72.98,"OTHER"),("Vapi Ind.",20.37,72.90,"OTHER")]
SEED_FACILITIES = [Facility(f"FAC-{i:03d}", *row) for i,row in enumerate(_NAMES,1)]


def load_facilities(data_dir: Path | str) -> gpd.GeoDataFrame:
    files = sorted((Path(data_dir)/"raw"/"registry").glob("*.csv"))
    frames = [pd.DataFrame([asdict(x) for x in SEED_FACILITIES])]
    frames += [pd.read_csv(p) for p in files]
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["name"])
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")


def nearest_facility(gdf: gpd.GeoDataFrame, lat: float, lon: float):
    if gdf is None or gdf.empty: return None, math.inf
    projected = gdf.to_crs("EPSG:7755")
    point = gpd.GeoSeries(gpd.points_from_xy([lon],[lat]), crs="EPSG:4326").to_crs("EPSG:7755").iloc[0]
    distances = projected.geometry.distance(point)
    idx = distances.idxmin(); distance = float(distances.loc[idx])
    if distance > 10_000: return None, distance
    row = gdf.loc[idx]
    return Facility(str(row.facility_id), str(row["name"]), float(row.lat), float(row.lon), str(row.sector),
                    str(row.get("district", "")), str(row.get("state", "")), str(row.get("source_of_truth", "MANUAL"))), distance


# ---------------------------------------------------------------------------
# Weak-label assignment
# ---------------------------------------------------------------------------

_SECTOR_LABEL: dict[str, tuple[str, str]] = {
    "REFI_GAS": ("FLARE", "high"),
    "FERTILIZER": ("FLARE", "high"),
    "STEEL": ("IND_FIRE", "medium"),
    "POWER": ("IND_FIRE", "medium"),
    "COAL": ("COAL", "medium"),
    "CEMENT": ("COAL", "medium"),
}

LANDCOVER_WILD = {"forest", "grassland", "shrub"}
PROXIMITY_LABEL_M = 2000
WILD_DIST_M = 5000
NEGATIVE_MIN_KM = 8
NEGATIVE_MAX_KM = 25


def label_sources(
    sources_df: pd.DataFrame,
    facilities_gdf: gpd.GeoDataFrame,
    landcover: Optional[pd.Series] = None,
    max_dist_m: float = PROXIMITY_LABEL_M,
) -> pd.DataFrame:
    """Assign weak labels to persistent-source clusters.

    Parameters
    ----------
    sources_df : pd.DataFrame
        Output of ``agnivani.geo.cluster.cluster_sources``.
    facilities_gdf : gpd.GeoDataFrame
        Output of ``load_facilities``.
    landcover : pd.Series, optional
        Index-aligned series of landcover-class strings (one per source).
        If None, all non-proximity labels become UNLABELLED.
    max_dist_m : float
        Proximity threshold (metres) for assigning a proximity-based label.

    Returns
    -------
    pd.DataFrame
        Copy of ``sources_df`` with columns ``label`` and ``label_confidence``.
    """
    out = sources_df.copy()
    out["label"] = "UNLABELLED"
    out["label_confidence"] = "none"

    for i, s in out.iterrows():
        lat, lon = float(s.centroid_lat), float(s.centroid_lon)
        facility, dist_m = nearest_facility(facilities_gdf, lat, lon)

        if facility is not None and dist_m <= max_dist_m:
            sector = str(facility.sector).upper()
            if sector in _SECTOR_LABEL:
                label, conf = _SECTOR_LABEL[sector]
                out.at[i, "label"] = label
                out.at[i, "label_confidence"] = conf
        elif dist_m > WILD_DIST_M:
            lc = ""
            if landcover is not None and i < len(landcover):
                lc = str(landcover.iloc[i]).lower().strip()
            if lc in LANDCOVER_WILD:
                out.at[i, "label"] = "WILD"
                out.at[i, "label_confidence"] = "high"

    return out


# ---------------------------------------------------------------------------
# Negative-control sampling
# ---------------------------------------------------------------------------

def sample_negative_controls(
    labelled: pd.DataFrame,
    facilities_gdf: gpd.GeoDataFrame,
    n_samples: int = 5,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate hard-negative control points for FLARE-labelled clusters.

    For each source flagged FLARE, sample ``n_samples`` random points in the
    annulus [8, 25] km from the same facility.  Each sampled point receives
    label UNLABELLED (landcover unknown).  These are hard negatives that teach
    the model "not every pixel near a refinery is a flare".

    Returns
    -------
    pd.DataFrame
        Rows conforming to the ``labelled`` schema with ``is_control=True``,
        ready to concatenate onto ``labelled``.
    """
    rng = random.Random(seed)
    controls: list[dict] = []

    flare_mask = labelled["label"] == "FLARE"
    flare_ids = labelled.loc[flare_mask, "source_id"].tolist()

    for src_id in flare_ids:
        row = labelled.loc[labelled["source_id"] == src_id].iloc[0]
        src_lat, src_lon = float(row.centroid_lat), float(row.centroid_lon)

        facility, _ = nearest_facility(facilities_gdf, src_lat, src_lon)
        if facility is None:
            anchor_lat, anchor_lon = src_lat, src_lon
        else:
            anchor_lat, anchor_lon = float(facility.lat), float(facility.lon)

        for _ in range(n_samples):
            bearing_deg = rng.uniform(0, 360)
            radius_km = rng.uniform(NEGATIVE_MIN_KM, NEGATIVE_MAX_KM)
            # Equirectangular approximation (fine for < 30 km)
            lat_rad = math.radians(anchor_lat)
            lon_rad = math.radians(anchor_lon)
            b_rad = math.radians(bearing_deg)
            d = radius_km / 6371.0
            new_lat = math.asin(
                math.sin(lat_rad) * math.cos(d)
                + math.cos(lat_rad) * math.sin(d) * math.cos(b_rad)
            )
            new_lon = lon_rad + math.atan2(
                math.sin(b_rad) * math.sin(d) * math.cos(lat_rad),
                math.cos(d) - math.sin(lat_rad) * math.sin(new_lat)
            )
            new_lat_deg = math.degrees(new_lat)
            new_lon_deg = math.degrees(new_lon)

            controls.append({
                "source_id": f"CTRL-{src_id}-{rng.randrange(10000):04d}",
                "centroid_lat": round(new_lat_deg, 6),
                "centroid_lon": round(new_lon_deg, 6),
                "label": "UNLABELLED",
                "label_confidence": "none",
                "is_control": True,
                # Carry over metadata so downstream features can still be built
                "n_hits": 0, "n_days": 0, "n_nights": 0, "night_frac": 0.0,
                "first_seen": pd.NaT, "last_seen": pd.NaT,
                "span_days": 0, "frp_mean": 0.0, "frp_max": 0.0,
                "frp_median": 0.0, "frp_cv": 0.0,
                "ti4_median": 300.0, "ti4_max": 300.0,
                "ti5_median": 270.0, "dT_median": 30.0,
                "ti4_std": 0.0, "local_solar_hour": 12.0,
                "pixel_area_m2": 375 ** 2,
                "cluster_extent_m": 0.0, "fill_ratio": 0.0,
                "recurrence_gap_days": 0.0, "flare_score": 0.0,
            })

    if not controls:
        return pd.DataFrame()
    ctrl_df = pd.DataFrame(controls)
    # Reorder columns to match labelled schema + is_control at end
    want_cols = list(labelled.columns) + ["is_control"]
    existing = [c for c in want_cols if c in ctrl_df.columns]
    extra = [c for c in ctrl_df.columns if c not in want_cols]
    ctrl_df = ctrl_df[existing + extra]
    return ctrl_df


# ---------------------------------------------------------------------------
# QA report & save helper
# ---------------------------------------------------------------------------

def qa_report(labelled: pd.DataFrame, facilities_gdf: gpd.GeoDataFrame) -> str:
    """Print and return a human-readable QA report."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("LABELLED DATASET — QA REPORT")
    lines.append("=" * 60)

    total = len(labelled)
    control_col = labelled.get("is_control")
    control_count = int(control_col.sum()) if control_col is not None else 0
    real = total - control_count

    lines.append(f"\nTotal rows: {total}  (real={real}, controls={control_count})")

    lines.append("\nRows per class:")
    for cls, cnt in labelled["label"].value_counts().items():
        lines.append(f"  {cls:>12s}: {cnt:5d}")

    unlabelled = (labelled["label"] == "UNLABELLED").sum()
    lines.append(f"\n% UNLABELLED: {unlabelled / total * 100:.1f}%")

    def _is_control(row):
        col = row.get("is_control")
        return bool(col) if col is not None else False

    lines.append("\nMedian distance to nearest facility (m) per class:")
    for cls in labelled["label"].unique():
        mask = (labelled["label"] == cls) & ~labelled.apply(_is_control, axis=1)
        subset = labelled[mask]
        if subset.empty:
            continue
        dists = []
        for _, s in subset.iterrows():
            _, d = nearest_facility(facilities_gdf, s.centroid_lat, s.centroid_lon)
            dists.append(d)
        if dists:
            lines.append(f"  {cls:>12s}: median={np.median(dists):>10.0f} m")

    lines.append("\nRegistry gaps (clusters with no facility within 50 km):")
    gaps: list[dict] = []
    for _, s in labelled.iterrows():
        if _is_control(s):
            continue
        fac, d = nearest_facility(facilities_gdf, s.centroid_lat, s.centroid_lon)
        if fac is None or d > 50_000:
            gaps.append({
                "source_id": s.source_id,
                "centroid_lat": s.centroid_lat,
                "centroid_lon": s.centroid_lon,
                "label": s.label,
                "dist_to_nearest_m": d if fac else float("inf"),
            })
    lines.append(f"  Gap count: {len(gaps)}")
    for g in gaps[:10]:
        lines.append(
            f"    {g['source_id']}: ({g['centroid_lat']:.4f},{g['centroid_lon']:.4f})"
            f" label={g['label']} dist={g['dist_to_nearest_m']:.0f} m"
        )
    if len(gaps) > 10:
        lines.append(f"    ... and {len(gaps) - 10} more (see registry_gaps.parquet)")

    return "\n".join(lines)


def save_labelled(
    sources_df: pd.DataFrame,
    facilities_gdf: gpd.GeoDataFrame | None = None,
    data_dir: Path | None = None,
    landcover: Optional[pd.Series] = None,
) -> None:
    """Full pipeline: label -> negative controls -> QA -> write parquet.

    If ``facilities_gdf`` is not provided and ``data_dir`` is given, loads
    from ``data/processed/facilities.parquet`` (the output of build_registry).
    Falls back to ``load_facilities()`` when neither is supplied.
    """
    if facilities_gdf is None and data_dir is not None:
        enriched = Path(data_dir) / "processed" / "facilities.parquet"
        if enriched.exists():
            facilities_gdf = gpd.read_parquet(enriched)
            print(f"[info] loaded enriched registry from {enriched} ({len(facilities_gdf)} facilities)")
        else:
            facilities_gdf = load_facilities(data_dir)
            print(f"[info] no enriched registry found; using seed-only ({len(facilities_gdf)} facilities)")
    elif facilities_gdf is None:
        raise ValueError("provide either facilities_gdf or data_dir")

    labelled = label_sources(sources_df, facilities_gdf, landcover=landcover)
    controls = sample_negative_controls(labelled, facilities_gdf)
    if not controls.empty:
        labelled = pd.concat([labelled, controls], ignore_index=True)

    report = qa_report(labelled, facilities_gdf)
    # Use ASCII-safe chars for Windows console compatibility
    safe_report = report.replace("->", "->")
    print(safe_report)

    # Save registry gaps for downstream inspection
    def _is_ctrl(s):
        col = s.get("is_control")
        return bool(col) if col is not None else False

    gaps_rows = []
    for _, s in labelled.iterrows():
        if _is_ctrl(s):
            continue
        fac, d = nearest_facility(facilities_gdf, s.centroid_lat, s.centroid_lon)
        if fac is None or d > 50_000:
            gaps_rows.append({
                "source_id": s.source_id,
                "centroid_lat": s.centroid_lat,
                "centroid_lon": s.centroid_lon,
                "label": s.label,
                "dist_to_nearest_m": d if fac else float("inf"),
            })
    gaps_path = data_dir / "processed" / "registry_gaps.parquet"
    if gaps_rows:
        pd.DataFrame(gaps_rows).to_parquet(gaps_path, index=False)
        print(f"[ok] registry gaps saved -> {gaps_path} ({len(gaps_rows)} rows)")
    else:
        print(f"[ok] no registry gaps found; skipping {gaps_path}")

    out_path = data_dir / "processed" / "labelled.parquet"
    labelled.to_parquet(out_path, index=False)
    print(f"[ok] labelled.parquet written -> {out_path} ({len(labelled)} rows)")
