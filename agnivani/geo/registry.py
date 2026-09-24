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
    match_radius_m: float | None = None


# Geocode correction & match radius justification:
# - Hazira LNG/Steel: Old coordinates (21.13, 72.64) were located at an administrative gate/office node,
#   ~2.7 km north of the actual industrial flare stacks and thermal operations.
#   Updated to (21.1055, 72.6405), the empirical centroid of the continuous thermal cluster
#   observed across VIIRS NOAA-20, NOAA-21, and Suomi-NPP passes (21.099–21.114 N, 72.632–72.653 E).
#   Assigned an explicit match_radius_m of 3500 m to cover the contiguous industrial complex
#   spanning AM/NS Steel, Reliance Hazira, Shell LNG, and ONGC gas processing plants.
_NAMES = [
("Jamnagar Refinery",22.35,70.02,"REFI_GAS"),("Vadinar Refinery",22.56,69.73,"REFI_GAS"),("Kandla Port",23.,70.22,"OTHER"),
("Hazira LNG/Steel",21.1055,72.6405,"REFI_GAS",3500.0),("Dahej LNG",21.71,72.58,"REFI_GAS"),("Mumbai High/Uran",18.88,72.95,"REFI_GAS"),
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

SEED_FACILITIES = []
for i, row in enumerate(_NAMES, 1):
    fac_id = f"FAC-{i:03d}"
    name, lat, lon, sector = row[0], row[1], row[2], row[3]
    radius = float(row[4]) if len(row) > 4 and row[4] is not None else None
    SEED_FACILITIES.append(Facility(fac_id, name, lat, lon, sector, match_radius_m=radius))


def load_facilities(data_dir: Path | str) -> gpd.GeoDataFrame:
    files = sorted((Path(data_dir)/"raw"/"registry").glob("*.csv"))
    frames = [pd.DataFrame([asdict(x) for x in SEED_FACILITIES])]
    frames += [pd.read_csv(p) for p in files]
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["name"])
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")


def nearest_facility(gdf: gpd.GeoDataFrame, lat: float, lon: float, max_dist_m: float | None = None):
    if gdf is None or gdf.empty: return None, math.inf
    projected = gdf.to_crs("EPSG:7755")
    point = gpd.GeoSeries(gpd.points_from_xy([lon],[lat]), crs="EPSG:4326").to_crs("EPSG:7755").iloc[0]
    distances = projected.geometry.distance(point)
    idx = distances.idxmin(); distance = float(distances.loc[idx])
    row = gdf.loc[idx]
    
    from agnivani.config import get_settings
    default_radius = float(get_settings().facility_match_radius_m)
    row_radius = row.get("match_radius_m")
    fac_radius = float(row_radius) if (row_radius is not None and pd.notna(row_radius)) else (max_dist_m if max_dist_m is not None else default_radius)
    if distance > fac_radius: return None, distance

    return Facility(
        str(row.facility_id), str(row["name"]), float(row.lat), float(row.lon), str(row.sector),
        str(row.get("district", "")), str(row.get("state", "")), str(row.get("source_of_truth", "MANUAL")),
        match_radius_m=float(row_radius) if (row_radius is not None and pd.notna(row_radius)) else None
    ), distance


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

        eff_max = (facility.match_radius_m if (facility and facility.match_radius_m is not None) else max_dist_m)
        if facility is not None and dist_m <= eff_max:
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
# Synthetic thermal blob generation
# ---------------------------------------------------------------------------

_WILD_FOREST_ANCHORS = [
    (23.5, 80.8), (21.6, 86.3), (29.5, 78.9), (26.6, 93.3),
    (11.5, 76.5), (21.9, 88.8), (24.2, 81.1), (13.8, 75.1),
    (18.2, 82.5), (26.1, 92.5), (22.5, 82.0), (14.5, 75.5),
]


def generate_synthetic_blobs(
    facilities_gdf: Optional[gpd.GeoDataFrame] = None,
    n_per_sector: int = 40,
    seed: int = 42,
    data_dir: Optional[Path | str] = None,
) -> pd.DataFrame:
    """Synthesize physics-grounded thermal clusters matching facility sectors and landcover.

    Generates synthetic thermal clusters for each of the 5 classes:
      - FLARE/REFI_GAS : high night_frac, low frp_cv, t_fire_K 1200-1800, span_days >= 5
      - COAL           : cool ti4, large cluster_extent_m, span_days >= 60
      - IND_FIRE       : short span, high frp_max
      - WILD           : forest/grassland landcover, daytime local_solar_hour, dist_facility_m > 5000
      - LEAK           : no MIR excess (t_fire_K null) near gas sector

    Parameters
    ----------
    facilities_gdf : gpd.GeoDataFrame, optional
        Loaded facility registry. If None, loaded via load_facilities(data_dir).
    n_per_sector : int, default 40
        Number of synthetic clusters to synthesize per sector/class.
    seed : int, default 42
        Random seed for reproducibility.
    data_dir : Path or str, optional
        If provided, merges real + synthetic into data_dir/processed/labelled.parquet.

    Returns
    -------
    pd.DataFrame
        Synthetic clusters with all 25 raw columns, label, label_confidence,
        origin='synthetic', and the 37 FEATURES columns from build_features.
    """
    from agnivani.features.build import build_features, FEATURES
    from agnivani.models.scorer import CLASSES

    rng = random.Random(seed)

    if facilities_gdf is None:
        p = Path(data_dir or "data") / "processed" / "facilities.parquet"
        if p.exists():
            facilities_gdf = gpd.read_parquet(p)
        else:
            facilities_gdf = load_facilities(data_dir or Path("data"))

    def _offset(lat: float, lon: float, dist_m: float, bearing_deg: float) -> tuple[float, float]:
        d_lat = (dist_m * math.cos(math.radians(bearing_deg))) / 111320.0
        d_lon = (dist_m * math.sin(math.radians(bearing_deg))) / (111320.0 * math.cos(math.radians(lat)))
        return round(lat + d_lat, 6), round(lon + d_lon, 6)

    refi_facs = facilities_gdf[facilities_gdf["sector"].isin(["REFI_GAS", "FERTILIZER"])]
    if refi_facs.empty:
        refi_facs = facilities_gdf

    coal_facs = facilities_gdf[facilities_gdf["sector"].isin(["COAL", "CEMENT"])]
    if coal_facs.empty:
        coal_facs = facilities_gdf

    ind_facs = facilities_gdf[facilities_gdf["sector"].isin(["STEEL", "POWER", "OTHER"])]
    if ind_facs.empty:
        ind_facs = facilities_gdf

    records: list[dict] = []

    # 1. FLARE
    for i in range(n_per_sector):
        fac = refi_facs.iloc[i % len(refi_facs)]
        dist_m = rng.uniform(200.0, 1200.0)
        c_lat, c_lon = _offset(float(fac.lat), float(fac.lon), dist_m, rng.uniform(0, 360))
        n_hits = rng.randint(20, 100)
        night_frac = rng.uniform(0.70, 0.95)
        n_nights = int(n_hits * night_frac)
        n_days = rng.randint(8, 40)
        span_days = rng.randint(max(5, n_days), 60)
        frp_cv = rng.uniform(0.15, 0.40)
        frp_mean = rng.uniform(10.0, 25.0)
        frp_max = rng.uniform(15.0, 40.0)
        frp_median = rng.uniform(9.0, 24.0)
        ti4_median = rng.uniform(345.0, 365.0)
        ti4_max = ti4_median + rng.uniform(5.0, 15.0)
        ti4_std = rng.uniform(2.0, 6.0)
        ti5_median = rng.uniform(290.0, 298.0)
        first_seen = pd.Timestamp("2026-08-01", tz="UTC") + pd.Timedelta(days=rng.randint(0, 5))
        last_seen = first_seen + pd.Timedelta(days=span_days)

        records.append({
            "source_id": f"SYN-FLARE-{i+1:04d}", "centroid_lat": c_lat, "centroid_lon": c_lon,
            "n_hits": n_hits, "n_days": n_days, "n_nights": n_nights, "night_frac": night_frac,
            "span_days": span_days, "frp_mean": frp_mean, "frp_max": frp_max, "frp_median": frp_median,
            "frp_cv": frp_cv, "ti4_median": ti4_median, "ti4_max": ti4_max, "ti4_std": ti4_std,
            "ti5_median": ti5_median, "dT_median": ti4_median - ti5_median,
            "local_solar_hour": rng.choice([21.0, 22.0, 23.0, 1.0, 2.0, 3.0]),
            "cluster_extent_m": rng.uniform(100.0, 450.0), "fill_ratio": rng.uniform(0.75, 1.0),
            "recurrence_gap_days": rng.uniform(0.5, 2.0), "flare_score": rng.uniform(25.0, 55.0),
            "pixel_area_m2": 375**2, "first_seen": first_seen, "last_seen": last_seen,
            "label": "FLARE", "label_confidence": "high",
            "t_fire_K": rng.uniform(1520.0, 1750.0), "landcover_class": "built",
            "diurnal_shape": "FLAT_24H", "diurnal_hist": [1.0 / 24.0] * 24,
        })

    # 2. COAL
    for i in range(n_per_sector):
        fac = coal_facs.iloc[i % len(coal_facs)]
        dist_m = rng.uniform(300.0, 1800.0)
        c_lat, c_lon = _offset(float(fac.lat), float(fac.lon), dist_m, rng.uniform(0, 360))
        n_hits = rng.randint(40, 150)
        night_frac = rng.uniform(0.3, 0.6)
        n_nights = int(n_hits * night_frac)
        n_days = rng.randint(30, 80)
        span_days = rng.randint(65, 200)
        frp_cv = rng.uniform(0.2, 0.4)
        frp_max = rng.uniform(1.8, 4.2)
        frp_mean = rng.uniform(1.2, 3.0)
        frp_median = rng.uniform(1.0, 2.8)
        ti4_median = rng.uniform(312.0, 325.0)
        ti4_max = ti4_median + rng.uniform(3.0, 8.0)
        ti4_std = rng.uniform(1.5, 3.5)
        ti5_median = rng.uniform(295.0, 302.0)
        first_seen = pd.Timestamp("2026-05-01", tz="UTC") + pd.Timedelta(days=rng.randint(0, 15))
        last_seen = first_seen + pd.Timedelta(days=span_days)

        records.append({
            "source_id": f"SYN-COAL-{i+1:04d}", "centroid_lat": c_lat, "centroid_lon": c_lon,
            "n_hits": n_hits, "n_days": n_days, "n_nights": n_nights, "night_frac": night_frac,
            "span_days": span_days, "frp_mean": frp_mean, "frp_max": frp_max, "frp_median": frp_median,
            "frp_cv": frp_cv, "ti4_median": ti4_median, "ti4_max": ti4_max, "ti4_std": ti4_std,
            "ti5_median": ti5_median, "dT_median": ti4_median - ti5_median,
            "local_solar_hour": rng.uniform(12.0, 15.0),
            "cluster_extent_m": rng.uniform(1200.0, 2600.0), "fill_ratio": rng.uniform(0.4, 0.8),
            "recurrence_gap_days": rng.uniform(1.0, 3.0), "flare_score": rng.uniform(1.0, 6.0),
            "pixel_area_m2": 375**2, "first_seen": first_seen, "last_seen": last_seen,
            "label": "COAL", "label_confidence": "high",
            "t_fire_K": rng.uniform(700.0, 920.0), "landcover_class": "built",
            "diurnal_shape": "FLAT_24H", "diurnal_hist": [1.0 / 24.0] * 24,
        })

    # 3. IND_FIRE
    for i in range(n_per_sector):
        fac = ind_facs.iloc[i % len(ind_facs)]
        dist_m = rng.uniform(200.0, 1500.0)
        c_lat, c_lon = _offset(float(fac.lat), float(fac.lon), dist_m, rng.uniform(0, 360))
        n_hits = rng.randint(2, 8)
        night_frac = rng.uniform(0.2, 0.6)
        n_nights = int(n_hits * night_frac)
        n_days = rng.randint(1, 2)
        span_days = rng.randint(1, 3)
        frp_max = rng.uniform(25.0, 90.0)
        frp_mean = rng.uniform(22.0, 75.0)
        frp_median = rng.uniform(20.0, 70.0)
        frp_cv = rng.uniform(0.4, 0.9)
        ti4_median = rng.uniform(345.0, 375.0)
        ti4_max = ti4_median + rng.uniform(10.0, 45.0)
        ti4_std = rng.uniform(5.0, 15.0)
        ti5_median = rng.uniform(295.0, 305.0)
        first_seen = pd.Timestamp("2026-08-25", tz="UTC") + pd.Timedelta(days=rng.randint(0, 3))
        last_seen = first_seen + pd.Timedelta(days=span_days)
        h_ind = int(rng.uniform(10.0, 18.0)) % 24
        hist_ind = [0.01] * 24
        hist_ind[h_ind] = 0.55
        hist_ind[(h_ind + 1) % 24] = 0.21
        hist_ind[-1] = max(0.0, 1.0 - sum(hist_ind[:-1]))

        records.append({
            "source_id": f"SYN-INDFIRE-{i+1:04d}", "centroid_lat": c_lat, "centroid_lon": c_lon,
            "n_hits": n_hits, "n_days": n_days, "n_nights": n_nights, "night_frac": night_frac,
            "span_days": span_days, "frp_mean": frp_mean, "frp_max": frp_max, "frp_median": frp_median,
            "frp_cv": frp_cv, "ti4_median": ti4_median, "ti4_max": ti4_max, "ti4_std": ti4_std,
            "ti5_median": ti5_median, "dT_median": ti4_median - ti5_median,
            "local_solar_hour": float(h_ind),
            "cluster_extent_m": rng.uniform(200.0, 600.0), "fill_ratio": rng.uniform(0.7, 1.0),
            "recurrence_gap_days": 0.0, "flare_score": rng.uniform(5.0, 14.0),
            "pixel_area_m2": 375**2, "first_seen": first_seen, "last_seen": last_seen,
            "label": "IND_FIRE", "label_confidence": "high",
            "t_fire_K": rng.uniform(1100.0, 1400.0), "landcover_class": "built",
            "diurnal_shape": "SPIKE_DECAY", "diurnal_hist": hist_ind,
        })

    # 4. WILD
    for i in range(n_per_sector):
        anchor_lat, anchor_lon = _WILD_FOREST_ANCHORS[i % len(_WILD_FOREST_ANCHORS)]
        c_lat, c_lon = _offset(anchor_lat, anchor_lon, rng.uniform(1000.0, 5000.0), rng.uniform(0, 360))
        n_hits = rng.randint(3, 15)
        night_frac = rng.uniform(0.0, 0.15)
        n_nights = int(n_hits * night_frac)
        n_days = rng.randint(1, 4)
        span_days = rng.randint(2, 8)
        frp_mean = rng.uniform(15.0, 45.0)
        frp_max = rng.uniform(20.0, 70.0)
        frp_median = rng.uniform(12.0, 40.0)
        frp_cv = rng.uniform(0.25, 0.55)
        ti4_median = rng.uniform(335.0, 355.0)
        ti4_max = ti4_median + rng.uniform(10.0, 20.0)
        ti4_std = rng.uniform(2.5, 6.0)
        ti5_median = rng.uniform(296.0, 305.0)
        first_seen = pd.Timestamp("2026-08-20", tz="UTC") + pd.Timedelta(days=rng.randint(0, 5))
        last_seen = first_seen + pd.Timedelta(days=span_days)
        h_wild = rng.uniform(11.0, 15.0)
        hist_wild = [0.005] * 24
        for hw in range(10, 17):
            hist_wild[hw] = 0.12
        hist_wild[-1] = max(0.0, 1.0 - sum(hist_wild[:-1]))

        records.append({
            "source_id": f"SYN-WILD-{i+1:04d}", "centroid_lat": c_lat, "centroid_lon": c_lon,
            "n_hits": n_hits, "n_days": n_days, "n_nights": n_nights, "night_frac": night_frac,
            "span_days": span_days, "frp_mean": frp_mean, "frp_max": frp_max, "frp_median": frp_median,
            "frp_cv": frp_cv, "ti4_median": ti4_median, "ti4_max": ti4_max, "ti4_std": ti4_std,
            "ti5_median": ti5_median, "dT_median": ti4_median - ti5_median,
            "local_solar_hour": h_wild,
            "cluster_extent_m": rng.uniform(400.0, 1200.0), "fill_ratio": rng.uniform(0.5, 0.85),
            "recurrence_gap_days": rng.uniform(0.0, 1.0), "flare_score": rng.uniform(2.0, 8.0),
            "pixel_area_m2": 375**2, "first_seen": first_seen, "last_seen": last_seen,
            "label": "WILD", "label_confidence": "high",
            "t_fire_K": rng.uniform(850.0, 1150.0), "landcover_class": "forest",
            "diurnal_shape": "DAYTIME_ONLY", "diurnal_hist": hist_wild,
        })

    # 5. LEAK
    for i in range(n_per_sector):
        fac = refi_facs.iloc[i % len(refi_facs)]
        dist_m = rng.uniform(200.0, 1200.0)
        c_lat, c_lon = _offset(float(fac.lat), float(fac.lon), dist_m, rng.uniform(0, 360))
        n_hits = rng.randint(8, 35)
        night_frac = rng.uniform(0.65, 0.90)
        n_nights = int(n_hits * night_frac)
        n_days = rng.randint(5, 25)
        span_days = rng.randint(10, 45)
        frp_cv = rng.uniform(0.15, 0.40)
        frp_mean = rng.uniform(0.4, 1.5)
        frp_max = rng.uniform(0.8, 2.5)
        frp_median = rng.uniform(0.3, 1.4)
        ti4_median = rng.uniform(298.0, 302.0)
        ti4_max = ti4_median + rng.uniform(1.0, 3.0)
        ti4_std = rng.uniform(0.5, 1.5)
        ti5_median = rng.uniform(297.0, 301.0)
        first_seen = pd.Timestamp("2026-08-01", tz="UTC") + pd.Timedelta(days=rng.randint(0, 10))
        last_seen = first_seen + pd.Timedelta(days=span_days)

        records.append({
            "source_id": f"SYN-LEAK-{i+1:04d}", "centroid_lat": c_lat, "centroid_lon": c_lon,
            "n_hits": n_hits, "n_days": n_days, "n_nights": n_nights, "night_frac": night_frac,
            "span_days": span_days, "frp_mean": frp_mean, "frp_max": frp_max, "frp_median": frp_median,
            "frp_cv": frp_cv, "ti4_median": ti4_median, "ti4_max": ti4_max, "ti4_std": ti4_std,
            "ti5_median": ti5_median, "dT_median": ti4_median - ti5_median,
            "local_solar_hour": rng.choice([21.0, 22.0, 23.0, 1.0, 2.0]),
            "cluster_extent_m": rng.uniform(100.0, 350.0), "fill_ratio": rng.uniform(0.8, 1.0),
            "recurrence_gap_days": rng.uniform(0.5, 2.0), "flare_score": rng.uniform(0.5, 3.0),
            "pixel_area_m2": 375**2, "first_seen": first_seen, "last_seen": last_seen,
            "label": "LEAK", "label_confidence": "high",
            "t_fire_K": np.nan, "landcover_class": "built",
            "diurnal_shape": "FLAT_24H", "diurnal_hist": [1.0 / 24.0] * 24,
        })

    synth_raw = pd.DataFrame(records)

    # Compute exact 37 FEATURES via build_features to guarantee zero drift
    feats = build_features(synth_raw, facilities_gdf)
    for col in feats.columns:
        synth_raw[col] = feats[col].values
    synth_raw["origin"] = "synthetic"

    if data_dir is not None:
        lab_path = Path(data_dir) / "processed" / "labelled.parquet"
        if lab_path.exists():
            existing = pd.read_parquet(lab_path)
            if "origin" not in existing.columns:
                existing["origin"] = "real"
            missing_in_existing = set(FEATURES) - set(existing.columns)
            if missing_in_existing:
                ex_feats = build_features(existing, facilities_gdf)
                for col in ex_feats.columns:
                    existing[col] = ex_feats[col].values
            if (existing["label"] == "UNLABELLED").any():
                lc_col = existing["landcover_class"] if "landcover_class" in existing.columns else None
                relab = label_sources(existing, facilities_gdf, landcover=lc_col)
                existing["label"] = relab["label"].values
                existing["label_confidence"] = relab["label_confidence"].values
            real_subset = existing[existing["origin"] != "synthetic"]
            merged = pd.concat([real_subset, synth_raw], ignore_index=True)
        else:
            merged = synth_raw
        lab_path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(lab_path, index=False)
        print(f"[ok] merged {len(merged)} labelled rows (real + synthetic) -> {lab_path}")

    return synth_raw


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
