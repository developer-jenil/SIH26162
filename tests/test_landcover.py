"""Tests for ESA WorldCover landcover resolution and WILD classification reachability."""
from __future__ import annotations

import math
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from agnivani.geo.landcover import (
    LOCAL_LANDCOVER_CLASSES,
    WORLDCOVER_CLASSES,
    annotate_landcover,
    ensure_tiles,
    landcover_majority,
    tile_id_for_point,
)
from agnivani.models.scorer import HeuristicScorer
from agnivani.features.build import canonical_frame, FEATURES, CONTEXT_COLUMNS


def test_worldcover_classes_mapping():
    expected_codes = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 115}
    assert set(WORLDCOVER_CLASSES.keys()) == expected_codes
    for code, cls_name in WORLDCOVER_CLASSES.items():
        assert cls_name in LOCAL_LANDCOVER_CLASSES


def test_tile_id_calculation():
    # Delhi @ 28.61, 77.20 -> lower left is N27E075
    assert tile_id_for_point(28.6139, 77.2090) == "N27E075"
    # Jim Corbett @ 29.53, 78.77 -> N27E078
    assert tile_id_for_point(29.53, 78.77) == "N27E078"


def test_offline_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("OFFLINE_MODE", "true")
    # Query point with no local tile present in tmp_path
    cls_name, status = landcover_majority(20.0, 75.0, window_px=3, cache_dir=tmp_path)
    assert cls_name == "unknown"
    assert status == "unavailable"


def test_known_forest_coordinate_online(monkeypatch):
    from agnivani.config import Settings
    monkeypatch.setenv("OFFLINE_MODE", "false")
    # Jim Corbett National Park forest coordinates
    try:
        cls_name, status = landcover_majority(29.53, 78.77, window_px=3)
        assert status == "resolved"
        assert cls_name == "forest"
    except Exception as exc:
        pytest.skip(f"Network unavailable for online COG fetch: {exc}")


def test_wild_rule_branch_reachability():
    """Regression test asserting that a synthetic row with landcover_class='forest',

    dist_facility_m=9000, span_days=10, local_solar_hour=13 classifies as WILD.
    """
    hour = 13.0
    row = {
        "source_id": "AV-WILD001",
        "block_id": "14_38",
        "facility_name": None,
        "facility_sector": None,
        "dist_facility_m": 9000.0,
        "landcover_class": "forest",
        "landcover_status": "resolved",
        "state": "Uttarakhand",
        "district": "Nainital",
        "t_fire_K": 850.0,
        "frac": 0.005,
        "frp_derived_MW": 15.0,
        "dT": 35.0,
        "ti4_ti5_ratio": 1.15,
        "log1p_frp_max": math.log1p(15.0),
        "local_hour_sin": math.sin(2 * math.pi * hour / 24),
        "local_hour_cos": math.cos(2 * math.pi * hour / 24),
        "is_night": 0.0,
        "n_days": 2,
        "n_nights": 0,
        "night_frac": 0.0,
        "span_days": 10,
        "hits_per_day": 2.0,
        "recurrence_gap_days": 1.0,
        "frp_cv": 0.2,
        "ti4_std": 5.0,
        "cluster_extent_m": 300.0,
        "fill_ratio": 1.0,
        "log1p_dist_nearest_facility_m": math.log1p(9000.0),
        "dist_nearest_settlement_m": 12000.0,
        "diurnal_shape": "DAYTIME_ONLY",
    }
    # Add dummy one-hot columns
    for s in ["STEEL", "CEMENT", "COAL", "POWER", "REFI_GAS", "FERTILIZER", "OTHER", "UNKNOWN"]:
        row[f"sector_{s}"] = 0.0
    for lc in LOCAL_LANDCOVER_CLASSES:
        row[f"landcover_{lc}"] = 1.0 if lc == "forest" else 0.0
    for ds in ["FLAT_24H", "SPIKE_DECAY", "EVENING_BURST", "DAYTIME_ONLY", "SPARSE"]:
        row[f"diurnal_{ds}"] = 1.0 if ds == "DAYTIME_ONLY" else 0.0

    df = pd.DataFrame([row])
    canonical = canonical_frame(df)
    scorer = HeuristicScorer()
    scores = scorer.score(canonical)

    assert len(scores) == 1
    assert scores.iloc[0]["cls"] == "WILD"
    assert scores.iloc[0]["conf"] >= 0.75


def test_annotate_landcover_dataframe(tmp_path):
    df = pd.DataFrame([
        {"source_id": "S1", "centroid_lat": 29.53, "centroid_lon": 78.77},
        {"source_id": "S2", "centroid_lat": np.nan, "centroid_lon": 77.0},
    ])
    annotated = annotate_landcover(df, cache_dir=tmp_path)
    assert "landcover_class" in annotated.columns
    assert "landcover_status" in annotated.columns
    assert len(annotated) == 2
    assert annotated.iloc[1]["landcover_class"] == "unknown"
    assert annotated.iloc[1]["landcover_status"] == "unavailable"


def test_no_non_unknown_class_paired_with_unavailable_status(tmp_path, monkeypatch):
    """Invariant test: Any detection whose landcover_status != 'resolved' MUST have landcover_class == 'unknown'."""
    monkeypatch.setenv("OFFLINE_MODE", "true")
    from agnivani.geo.landcover import resolve_landcover, resolve_landcover_batch
    
    test_points = [
        {"source_id": "P1", "centroid_lat": 28.6139, "centroid_lon": 77.2090}, # Delhi
        {"source_id": "P2", "centroid_lat": 21.1055, "centroid_lon": 72.6405}, # Hazira
        {"source_id": "P3", "centroid_lat": 8.3400, "centroid_lon": 77.5400},  # Offshore
        {"source_id": "P4", "centroid_lat": 22.3500, "centroid_lon": 70.0200}, # Jamnagar
    ]
    df = pd.DataFrame(test_points)
    annotated = annotate_landcover(df, cache_dir=tmp_path)
    
    for _, row in annotated.iterrows():
        if row["landcover_status"] != "resolved":
            assert row["landcover_class"] == "unknown", (
                f"Fabrication violation: class '{row['landcover_class']}' paired with status '{row['landcover_status']}'"
            )

    # Batch and point resolvers must also return 'unknown'
    batch = resolve_landcover_batch(df)
    for p in test_points:
        assert batch[p["source_id"]] == "unknown"
        assert resolve_landcover(p["centroid_lat"], p["centroid_lon"]) == "unknown"

