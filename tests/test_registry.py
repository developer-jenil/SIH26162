"""Tests for agnivani.geo.registry — dedupe, labelling, negative controls."""
from __future__ import annotations

import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from agnivani.geo.registry import (
    PROXIMITY_LABEL_M,
    WILD_DIST_M,
    Facility,
    SEED_FACILITIES,
    label_sources,
    load_facilities,
    nearest_facility,
    sample_negative_controls,
)


# ---------------------------------------------------------------------------
# build_registry output invariants  (tests 1 & 4 are tested via fixtures below)
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_registry(tmp_path: Path) -> gpd.GeoDataFrame:
    """Empty raw dir — only MANUAL seed populated."""
    return load_facilities(tmp_path)


@pytest.fixture
def registry_with_csv(tmp_path: Path) -> gpd.GeoDataFrame:
    """Seed + one extra CSV row."""
    raw = tmp_path / "raw" / "registry"
    raw.mkdir(parents=True)
    (raw / "extra.csv").write_text(
        "facility_id,name,lat,lon,sector,district,state,source_of_truth\n"
        "FAC-900,Mumbai Thermal,19.10,72.85,POWER,Mumbai,MH,CSV\n",
        encoding="utf-8",
    )
    return load_facilities(tmp_path)


# ---------------------------------------------------------------------------
# Test 1 — no facility appears twice within 500 m after build
# ---------------------------------------------------------------------------

class TestNoDuplicateNearFacilities:
    def test_empty_registry_no_dups(self, empty_registry: gpd.GeoDataFrame):
        gdf = empty_registry
        self._assert_no_near_dups(gdf)

    def test_registry_with_extra_csv(self, registry_with_csv: gpd.GeoDataFrame):
        gdf = registry_with_csv
        self._assert_no_near_dups(gdf)

    @staticmethod
    def _assert_no_near_dups(gdf: gpd.GeoDataFrame):
        """Every pair of facilities must be > 500 m apart."""
        gdf_proj = gdf.to_crs("EPSG:7755")
        geom = gdf_proj.geometry
        n = len(geom)
        for i in range(n):
            for j in range(i + 1, n):
                d = float(geom[i].distance(geom[j]))
                assert d > 500, (
                    f"Two facilities within 500 m: {gdf.iloc[i]['name']} "
                    f"and {gdf.iloc[j]['name']} (dist={d:.0f} m)"
                )


# ---------------------------------------------------------------------------
# Test 2 — Hazira cluster gets a FLARE-family label
# ---------------------------------------------------------------------------

class TestHaziraFlareLabel:
    """Verify that sources near a REFI_GAS facility receive a FLARE label."""

    # Exact coordinates co-located with the Hazira facility (distance = 0 m).
    _HAZIRA_LAT = 21.13
    _HAZIRA_LON = 72.64

    def _make_sources(self) -> pd.DataFrame:
        return pd.DataFrame([
            dict(
                source_id="TEST-HZ-001",
                centroid_lat=self._HAZIRA_LAT,
                centroid_lon=self._HAZIRA_LON,
                n_hits=12, n_days=5, n_nights=7, night_frac=7 / 12,
                first_seen=pd.Timestamp("2026-08-29", tz="UTC"),
                last_seen=pd.Timestamp("2026-09-01", tz="UTC"),
                span_days=4, frp_mean=5.0, frp_max=9.54, frp_median=4.0,
                frp_cv=0.4, ti4_median=332.6, ti4_max=350.0, ti5_median=292.9,
                dT_median=39.7, ti4_std=4.0, local_solar_hour=22.0,
                pixel_area_m2=375 ** 2, cluster_extent_m=800.0,
                fill_ratio=1.0, recurrence_gap_days=1.0, flare_score=20.0,
            )
        ])

    def test_hazira_cluster_is_flare(self, empty_registry: gpd.GeoDataFrame):
        sources = self._make_sources()
        labelled = label_sources(sources, empty_registry)
        assert len(labelled) == 1
        assert labelled.iloc[0]["label"] == "FLARE", (
            f"Expected FLARE but got {labelled.iloc[0]['label']}"
        )
        assert labelled.iloc[0]["label_confidence"] == "high"

    def test_hazira_cluster_not_unlabelled(self, empty_registry: gpd.GeoDataFrame):
        sources = self._make_sources()
        labelled = label_sources(sources, empty_registry)
        assert labelled.iloc[0]["label"] != "UNLABELLED"

    def test_hazira_cluster_not_ind_fire_or_coal(self, empty_registry: gpd.GeoDataFrame):
        """Must land in the FLARE family, not mis-assigned."""
        sources = self._make_sources()
        labelled = label_sources(sources, empty_registry)
        assert labelled.iloc[0]["label"] in {"FLARE"}


# ---------------------------------------------------------------------------
# Test 3 — 15.18/76.66 cluster ends up UNLABELLED, not force-fit
# ---------------------------------------------------------------------------

class TestMangaloreUnlabelled:
    """The Mangalore-area cluster is ~318 km from any facility; must stay UNLABELLED."""

    _MGL_LAT = 15.18
    _MGL_LON = 76.66

    def _make_sources(self) -> pd.DataFrame:
        return pd.DataFrame([
            dict(
                source_id="TEST-MGL-001",
                centroid_lat=self._MGL_LAT,
                centroid_lon=self._MGL_LON,
                n_hits=6, n_days=2, n_nights=5, night_frac=5 / 6,
                first_seen=pd.Timestamp("2026-08-29", tz="UTC"),
                last_seen=pd.Timestamp("2026-09-01", tz="UTC"),
                span_days=3, frp_mean=3.0, frp_max=7.11, frp_median=3.5,
                frp_cv=0.3, ti4_median=323.0, ti4_max=340.0, ti5_median=286.0,
                dT_median=37.0, ti4_std=5.0, local_solar_hour=21.0,
                pixel_area_m2=375 ** 2, cluster_extent_m=600.0,
                fill_ratio=1.0, recurrence_gap_days=1.5, flare_score=15.0,
            )
        ])

    def test_mangalore_cluster_is_unlabelled(self, empty_registry: gpd.GeoDataFrame):
        sources = self._make_sources()
        labelled = label_sources(sources, empty_registry)
        assert len(labelled) == 1
        assert labelled.iloc[0]["label"] == "UNLABELLED", (
            f"Expected UNLABELLED but got {labelled.iloc[0]['label']}"
        )

    def test_mangalore_not_force_fit_to_flare(self, empty_registry: gpd.GeoDataFrame):
        sources = self._make_sources()
        labelled = label_sources(sources, empty_registry)
        assert labelled.iloc[0]["label"] != "FLARE"

    def test_mangalore_not_force_fit_to_ind_fire(self, empty_registry: gpd.GeoDataFrame):
        sources = self._make_sources()
        labelled = label_sources(sources, empty_registry)
        assert labelled.iloc[0]["label"] not in {"IND_FIRE", "COAL"}


# ---------------------------------------------------------------------------
# Test 4 — negative-control sampling shape
# ---------------------------------------------------------------------------

class TestNegativeControls:
    def test_generates_five_per_flare(self, empty_registry: gpd.GeoDataFrame):
        # Build a single FLARE source
        sources = pd.DataFrame([
            dict(
                source_id="SRC-FLARE-001",
                centroid_lat=22.35, centroid_lon=70.02,  # Jamnagar — inside REFI_GAS radius
                n_hits=12, n_days=5, n_nights=7, night_frac=7 / 12,
                first_seen=pd.Timestamp("2026-08-29", tz="UTC"),
                last_seen=pd.Timestamp("2026-09-01", tz="UTC"),
                span_days=4, frp_mean=5.0, frp_max=9.54, frp_median=4.0,
                frp_cv=0.4, ti4_median=332.6, ti4_max=350.0, ti5_median=292.9,
                dT_median=39.7, ti4_std=4.0, local_solar_hour=22.0,
                pixel_area_m2=375 ** 2, cluster_extent_m=800.0,
                fill_ratio=1.0, recurrence_gap_days=1.0, flare_score=20.0,
            )
        ])
        labelled = label_sources(sources, empty_registry)
        assert labelled.iloc[0]["label"] == "FLARE"

        controls = sample_negative_controls(labelled, empty_registry, n_samples=5)
        assert len(controls) == 5
        assert all(c["is_control"] for _, c in controls.iterrows())
        assert all(c["label"] == "UNLABELLED" for _, c in controls.iterrows())

    def test_no_controls_when_no_flare(self, empty_registry: gpd.GeoDataFrame):
        sources = self._make_non_flare_source()
        labelled = label_sources(sources, empty_registry)
        controls = sample_negative_controls(labelled, empty_registry)
        assert controls.empty

    @staticmethod
    def _make_non_flare_source() -> pd.DataFrame:
        """A source far from any facility → stays UNLABELLED."""
        return pd.DataFrame([
            dict(
                source_id="SRC-WILD-001",
                centroid_lat=8.5, centroid_lon=77.0,  # far south, no facility nearby
                n_hits=3, n_days=2, n_nights=1, night_frac=1 / 3,
                first_seen=pd.Timestamp("2026-08-30", tz="UTC"),
                last_seen=pd.Timestamp("2026-09-01", tz="UTC"),
                span_days=2, frp_mean=2.0, frp_max=3.0, frp_median=2.5,
                frp_cv=0.2, ti4_median=310.0, ti4_max=320.0, ti5_median=280.0,
                dT_median=30.0, ti4_std=3.0, local_solar_hour=14.0,
                pixel_area_m2=375 ** 2, cluster_extent_m=400.0,
                fill_ratio=1.0, recurrence_gap_days=1.0, flare_score=8.0,
            )
        ])


# ---------------------------------------------------------------------------
# Test 5 — nearest_facility returns None beyond 10 km cutoff
# ---------------------------------------------------------------------------

class TestNearestFacilityCutoff:
    def test_far_point_returns_none(self, empty_registry: gpd.GeoDataFrame):
        fac, dist = nearest_facility(empty_registry, 5.0, 75.0)
        assert fac is None
        assert dist > 10_000

    def test_close_point_returns_facility(self, empty_registry: gpd.GeoDataFrame):
        fac, dist = nearest_facility(empty_registry, 22.35, 70.02)
        assert fac is not None
        assert fac.name == "Jamnagar Refinery"
        assert dist < 10_000
