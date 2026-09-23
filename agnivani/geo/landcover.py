"""Lightweight landcover resolver with offline-safe fallback and parquet caching.

Resolves cluster centroids to one of the 8 canonical classes:
{forest, grassland, shrub, cropland, built, water, other, unknown}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import httpx
import numpy as np
import pandas as pd
from agnivani.geo.india import point_in_india

VALID_LANDCOVERS = {
    "forest", "grassland", "shrub", "cropland", "built", "water", "other", "unknown"
}

# In-memory session cache for fast repetitive lookups during pipeline runs
_MEMORY_CACHE: dict[str, str] = {}


def _cache_key(lat: float, lon: float) -> str:
    return f"{round(float(lat), 3):.3f}_{round(float(lon), 3):.3f}"


def _load_disk_cache(cache_path: Path) -> dict[str, str]:
    paths_to_check = [cache_path]
    project_cache = Path("data") / "processed" / "landcover.parquet"
    if project_cache not in paths_to_check:
        paths_to_check.append(project_cache)

    for p in paths_to_check:
        if p.exists():
            try:
                df = pd.read_parquet(p)
                if "key" in df.columns and "landcover_class" in df.columns:
                    return dict(zip(df["key"], df["landcover_class"]))
            except Exception:
                pass
    return {}


def _save_disk_cache(cache_path: Path, cache_dict: dict[str, str]):
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for k, lc in cache_dict.items():
            lat_str, lon_str = k.split("_")
            rows.append({
                "key": k,
                "centroid_lat": float(lat_str),
                "centroid_lon": float(lon_str),
                "landcover_class": lc,
            })
        pd.DataFrame(rows).to_parquet(cache_path, index=False)
    except Exception:
        pass


def _coarse_landcover(lat: float, lon: float) -> str:
    """Coarse rule-based landcover lookup for the Indian subcontinent.
    Ensures offline zero-crash operation without heavy raster dependencies.
    """
    # 1. Sea / Coastal Water check
    # Southern tip offshore & Arabian Sea / Indian Ocean waters (including AV-8A95CFFE @ 8.34, 77.54)
    if lat < 8.4 and (lon < 77.6 or lon > 78.0):
        return "water"
    if lat < 8.35:
        return "water"

    # Arabian Sea offshore (west of mainland coast)
    if lat < 10.0 and lon < 75.6:
        return "water"
    if 10.0 <= lat < 15.0 and lon < 73.6:
        return "water"
    if 15.0 <= lat < 19.0 and lon < 72.6:
        return "water"
    if 19.0 <= lat < 21.0 and lon < 72.3:
        return "water"
    if 21.0 <= lat < 24.0 and lon < 68.6:
        return "water"

    # Bay of Bengal offshore (east of mainland coast)
    if lat < 12.0 and lon > 80.2:
        return "water"
    if 12.0 <= lat < 16.0 and lon > 80.6:
        return "water"
    if 16.0 <= lat < 20.0 and lon > 82.8:
        return "water"
    if 20.0 <= lat < 22.5 and lon > 87.2:
        return "water"

    # Major water bodies (Chilika Lake, Vembanad, Pulicat, Gulf of Kutch core)
    if 19.55 <= lat <= 19.95 and 85.15 <= lon <= 85.65:
        return "water"
    if 22.5 <= lat <= 22.9 and 69.3 <= lon <= 70.1:
        return "water"

    # If entirely outside sovereign mainland polygon boundary, classify as water
    if not point_in_india(lon, lat):
        return "water"

    # 2. Forest belts
    # Western Ghats mountain forest strip
    if 8.5 <= lat <= 16.0 and 74.8 <= lon <= 77.0:
        return "forest"
    # Central Indian tribal/dense forest belt (Dandakaranya / Bastar / Satpura)
    if 18.5 <= lat <= 23.5 and 80.5 <= lon <= 84.5:
        return "forest"
    # North-East hill forests (Assam, Meghalaya, Arunachal, Nagaland)
    if 23.5 <= lat <= 28.5 and 91.5 <= lon <= 96.5:
        return "forest"
    # Himalayan foothills
    if 29.8 <= lat <= 33.5 and 76.5 <= lon <= 80.5:
        return "forest"

    # 3. Arid Shrub / Desert
    # Thar Desert and arid Kutch scrub
    if 24.5 <= lat <= 29.5 and 69.5 <= lon <= 73.5:
        return "shrub"

    # 4. Major Cropland agricultural heartlands (Indo-Gangetic & River Basins)
    # Punjab, Haryana, UP, Bihar, WB plains (e.g. 30.3, 75.8 in Punjab)
    if 24.0 <= lat <= 32.5 and 73.5 <= lon <= 88.5:
        return "cropland"
    # Deccan & coastal agricultural plains
    if 11.0 <= lat <= 22.0 and 74.5 <= lon <= 82.5:
        return "cropland"

    # Default for mainland India is agricultural cropland
    return "cropland"


def _fetch_stac_worldcover(lat: float, lon: float) -> Optional[str]:
    """Attempt single ESA WorldCover pixel class query via open STAC / web endpoint."""
    try:
        url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
        payload = {
            "collections": ["esa-worldcover"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "limit": 1
        }
        with httpx.Client(timeout=1.5) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    class_code = props.get("worldcover:class")
                    mapping = {
                        10: "forest",
                        20: "shrub",
                        30: "grassland",
                        40: "cropland",
                        50: "built",
                        60: "other",
                        80: "water",
                        90: "water",
                        95: "forest"
                    }
                    if class_code in mapping:
                        return mapping[class_code]
    except Exception:
        pass
    return None


def resolve_landcover(lat: float, lon: float, data_dir: Path | str = Path("data")) -> str:
    """Resolve a single (centroid_lat, centroid_lon) to one of the 8 canonical classes."""
    key = _cache_key(lat, lon)
    if key in _MEMORY_CACHE:
        return _MEMORY_CACHE[key]

    cache_path = Path(data_dir) / "processed" / "landcover.parquet"
    disk_cache = _load_disk_cache(cache_path)
    if key in disk_cache:
        _MEMORY_CACHE[key] = disk_cache[key]
        return disk_cache[key]

    # Preferred: ESA WorldCover / STAC point lookup
    lc = _fetch_stac_worldcover(lat, lon)
    if not lc or lc not in VALID_LANDCOVERS:
        # Fallback: Coarse built-in lookup
        lc = _coarse_landcover(lat, lon)

    # Update caches
    _MEMORY_CACHE[key] = lc
    disk_cache[key] = lc
    _save_disk_cache(cache_path, disk_cache)
    return lc


def resolve_landcover_batch(sources_df: pd.DataFrame, data_dir: Path | str = Path("data")) -> dict[str, str]:
    """Batch resolve landcover for all centroids in a sources dataframe."""
    result = {}
    cache_path = Path(data_dir) / "processed" / "landcover.parquet"
    disk_cache = _load_disk_cache(cache_path)
    updated = False

    for _, row in sources_df.iterrows():
        sid = str(row.get("source_id", ""))
        lat = float(row.get("centroid_lat", 0.0))
        lon = float(row.get("centroid_lon", 0.0))
        key = _cache_key(lat, lon)

        if key in _MEMORY_CACHE:
            lc = _MEMORY_CACHE[key]
        elif key in disk_cache:
            lc = disk_cache[key]
            _MEMORY_CACHE[key] = lc
        else:
            lc = _fetch_stac_worldcover(lat, lon)
            if not lc or lc not in VALID_LANDCOVERS:
                lc = _coarse_landcover(lat, lon)
            _MEMORY_CACHE[key] = lc
            disk_cache[key] = lc
            updated = True

        if sid:
            result[sid] = lc
        result[(round(lat, 3), round(lon, 3))] = lc

    if updated:
        _save_disk_cache(cache_path, disk_cache)

    return result
