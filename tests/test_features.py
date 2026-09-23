import pandas as pd
from agnivani.features.build import FEATURES,FORBIDDEN,build_features
from agnivani.geo.registry import load_facilities

def sources():
    base={"source_id":"A","n_hits":12,"n_days":5,"n_nights":7,"night_frac":7/12,"first_seen":pd.Timestamp("2026-08-29",tz="UTC"),"last_seen":pd.Timestamp("2026-09-01",tz="UTC"),"span_days":4,"frp_mean":5.,"frp_max":9.54,"frp_median":4.,"frp_cv":.4,"ti4_median":332.6,"ti4_max":350.,"ti5_median":292.9,"dT_median":39.7,"ti4_std":4.,"local_solar_hour":22.,"pixel_area_m2":375**2,"cluster_extent_m":800.,"fill_ratio":1.,"recurrence_gap_days":1.,"centroid_lat":21.10,"centroid_lon":72.64,"flare_score":20.}
    b=dict(base,source_id="B",n_hits=6,n_days=2,n_nights=5,centroid_lat=15.18,centroid_lon=76.66,frp_max=7.11)
    return pd.DataFrame([base,b])

def test_coordinate_free_and_registry_gap(tmp_path):
    x=build_features(sources(),load_facilities(tmp_path))
    assert not(set(FEATURES)&FORBIDDEN)
    assert x.iloc[0].facility_name=="Hazira LNG/Steel"
    assert x.iloc[1].facility_name is None and x.iloc[1].dist_facility_m>300_000

def test_landcover_cropland_and_water(tmp_path):
    from agnivani.geo.landcover import resolve_landcover
    assert resolve_landcover(30.3, 75.8, tmp_path) == "cropland"
    assert resolve_landcover(8.34184, 77.54288, tmp_path) == "water"

    cropland_cluster = pd.DataFrame([{
        "source_id": "CROP_1", "centroid_lat": 30.3, "centroid_lon": 75.8,
        "n_hits": 5, "n_days": 2, "n_nights": 1, "night_frac": 0.2,
        "first_seen": pd.Timestamp("2026-08-29", tz="UTC"), "last_seen": pd.Timestamp("2026-08-30", tz="UTC"),
        "span_days": 2, "frp_mean": 6.0, "frp_max": 8.0, "frp_median": 6.0, "frp_cv": 0.3,
        "ti4_median": 330.0, "ti4_max": 335.0, "ti5_median": 295.0, "dT_median": 35.0, "ti4_std": 2.0,
        "local_solar_hour": 14.0, "pixel_area_m2": 375**2, "cluster_extent_m": 500.0, "fill_ratio": 1.0,
        "recurrence_gap_days": 1.0, "flare_score": 10.0
    }])
    sea_cluster = pd.DataFrame([{
        "source_id": "SEA_1", "centroid_lat": 8.34184, "centroid_lon": 77.54288,
        "n_hits": 1, "n_days": 1, "n_nights": 0, "night_frac": 0.0,
        "first_seen": pd.Timestamp("2026-08-31", tz="UTC"), "last_seen": pd.Timestamp("2026-08-31", tz="UTC"),
        "span_days": 1, "frp_mean": 8.3, "frp_max": 8.3, "frp_median": 8.3, "frp_cv": 0.0,
        "ti4_median": 328.0, "ti4_max": 328.0, "ti5_median": 302.56, "dT_median": 25.44, "ti4_std": 0.0,
        "local_solar_hour": 13.0, "pixel_area_m2": 375**2, "cluster_extent_m": 0.0, "fill_ratio": 1.0,
        "recurrence_gap_days": 0.0, "flare_score": 5.0
    }])
    facs = load_facilities(tmp_path)
    feat_crop = build_features(cropland_cluster, facs)
    assert feat_crop.iloc[0]["landcover_cropland"] == 1.0
    assert feat_crop.iloc[0]["landcover_water"] == 0.0

    feat_sea = build_features(sea_cluster, facs)
    assert feat_sea.iloc[0]["landcover_water"] == 1.0
    assert feat_sea.iloc[0]["landcover_cropland"] == 0.0

def test_reproduce_av_8a95cffe_offshore_suppression(tmp_path):
    from agnivani.models.scorer import HeuristicScorer, CLASSES
    from agnivani.ingest.scheduler import build_records
    av_cluster = pd.DataFrame([{
        "source_id": "AV-8A95CFFE", "centroid_lat": 8.34184, "centroid_lon": 77.54288,
        "n_hits": 1, "n_days": 1, "n_nights": 0, "night_frac": 0.0,
        "first_seen": pd.Timestamp("2026-08-31 08:28:00", tz="UTC"), "last_seen": pd.Timestamp("2026-08-31 08:28:00", tz="UTC"),
        "span_days": 1, "frp_mean": 8.3, "frp_max": 8.3, "frp_median": 8.3, "frp_cv": 0.0,
        "ti4_median": 328.0, "ti4_max": 328.0, "ti5_median": 302.56, "dT_median": 25.44, "ti4_std": 0.0,
        "local_solar_hour": 13.0, "pixel_area_m2": 375**2, "cluster_extent_m": 0.0, "fill_ratio": 1.0,
        "recurrence_gap_days": 0.0, "flare_score": 5.0
    }])
    facs = load_facilities(tmp_path)
    feats = build_features(av_cluster, facs)
    assert feats.iloc[0]["landcover_water"] == 1.0

    scorer = HeuristicScorer()
    scores = scorer.score(feats)
    records = build_records(pd.DataFrame(), av_cluster, feats, scores)
    assert len(records) == 1
    rec = records[0]
    assert rec["offshore_suppressed"] is True
    assert rec["severity"] == "LOW"
    assert "suppressed" in rec["reason"].lower()
    assert rec["cited_rule"] == "OFFSHORE-SUPPRESSED"
    assert rec["cls"] in CLASSES
    assert abs(sum(rec["probs"].values()) - 1.0) < 1e-4

def test_scorer_backend_missing_artifacts_fails_loud(tmp_path):
    import pytest
    from agnivani.config import Settings
    from agnivani.models.scorer import get_scorer
    s = Settings(scorer_backend="xgboost", data_dir=tmp_path, offline_mode=True)
    with pytest.raises(FileNotFoundError, match="Train the model first"):
        get_scorer(s)

def test_train_k1_normalization_and_fail_loud(tmp_path):
    import pytest
    from agnivani.models.train import train
    proc_dir = tmp_path / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)

    # 1. Offending label outside CLASSES
    bad_df = pd.DataFrame([{
        "source_id": "BAD_1", "label": "UNKNOWN_OFFENDING_LABEL",
        "centroid_lat": 22.0, "centroid_lon": 70.0
    }])
    bad_df.to_parquet(proc_dir / "labelled.parquet", index=False)
    with pytest.raises(ValueError, match="Offending label"):
        train(tmp_path)

    # 2. Missing FEATURES fails loud
    valid_df = pd.DataFrame([{
        "source_id": "VALID_1", "label": "FLARE",
        "centroid_lat": 22.0, "centroid_lon": 70.0
    }])
    valid_df.to_parquet(proc_dir / "labelled.parquet", index=False)
    with pytest.raises(ValueError, match="missing required FEATURES"):
        train(tmp_path)


def test_synthetic_24h_uniform_cluster_is_flat():
    from agnivani.geo.cluster import cluster_sources
    import numpy as np

    # 24 detections across 24 hours at the same location
    rows = []
    base_time = pd.Timestamp("2026-08-30 00:30:00", tz="UTC")
    for h in range(24):
        t = base_time + pd.Timedelta(hours=h)
        rows.append({
            "latitude": 22.35, "longitude": 70.02,
            "bright_ti4": 340.0, "bright_ti5": 295.0,
            "frp": 12.0, "scan": 0.375, "track": 0.375,
            "acq_date": t.date(), "acq_time": f"{t.hour:02d}{t.minute:02d}",
            "acq_utc": t,
            "daynight": "N" if (h < 6 or h >= 18) else "D",
            "satellite": "N20", "instrument": "VIIRS",
            "local_solar_hour": float(h) + 0.5,
            "pixel_area_m2": 375**2
        })
    df = pd.DataFrame(rows)
    clustered = cluster_sources(df)
    assert len(clustered) == 1
    c = clustered.iloc[0]
    assert c["diurnal_shape"] == "FLAT_24H"
    assert len(c["diurnal_hist"]) == 24
    assert abs(sum(c["diurnal_hist"]) - 1.0) < 1e-5


def test_three_day_afternoon_cluster_is_daytime_only():
    from agnivani.geo.cluster import cluster_sources

    # 3 detections on 3 consecutive days in afternoon (e.g. 13:30, 14:00, 14:30)
    rows = []
    for day in range(3):
        t = pd.Timestamp(f"2026-08-{28+day} 14:00:00", tz="UTC")
        rows.append({
            "latitude": 28.50, "longitude": 77.20,
            "bright_ti4": 335.0, "bright_ti5": 298.0,
            "frp": 8.0, "scan": 0.375, "track": 0.375,
            "acq_date": t.date(), "acq_time": "1400",
            "acq_utc": t,
            "daynight": "D",
            "satellite": "N20", "instrument": "VIIRS",
            "local_solar_hour": 14.0,
            "pixel_area_m2": 375**2
        })
    df = pd.DataFrame(rows)
    clustered = cluster_sources(df)
    assert len(clustered) == 1
    c = clustered.iloc[0]
    assert c["diurnal_shape"] == "DAYTIME_ONLY"
    assert len(c["diurnal_hist"]) == 24
    assert abs(sum(c["diurnal_hist"]) - 1.0) < 1e-5


def test_heuristic_scorer_cropland_evening_burst_tie_breaker(tmp_path):
    from agnivani.features.build import build_features, FEATURES
    from agnivani.geo.registry import load_facilities
    from agnivani.models.scorer import HeuristicScorer, CLASSES

    cluster = pd.DataFrame([{
        "source_id": "STUBBLE_1", "centroid_lat": 30.5, "centroid_lon": 75.5,
        "n_hits": 8, "n_days": 2, "n_nights": 0, "night_frac": 0.0,
        "first_seen": pd.Timestamp("2026-09-01", tz="UTC"), "last_seen": pd.Timestamp("2026-09-02", tz="UTC"),
        "span_days": 2, "frp_mean": 15.0, "frp_max": 25.0, "frp_median": 14.0, "frp_cv": 0.3,
        "ti4_median": 340.0, "ti4_max": 350.0, "ti5_median": 295.0, "dT_median": 45.0, "ti4_std": 3.0,
        "local_solar_hour": 17.5, "pixel_area_m2": 375**2, "cluster_extent_m": 600.0, "fill_ratio": 1.0,
        "recurrence_gap_days": 1.0, "flare_score": 12.0,
        "diurnal_shape": "EVENING_BURST",
        "diurnal_hist": [0.0]*16 + [0.25, 0.35, 0.25, 0.15] + [0.0]*4,
        "landcover_class": "cropland"
    }])
    facs = load_facilities(tmp_path)
    feats = build_features(cluster, facs)
    assert feats.iloc[0]["landcover_cropland"] == 1.0
    assert feats.iloc[0]["diurnal_shape"] == "EVENING_BURST"
    assert feats.iloc[0]["diurnal_EVENING_BURST"] == 1.0

    scorer = HeuristicScorer()
    scored = scorer.score(feats)
    assert len(scored) == 1
    s = scored.iloc[0]
    assert s["cls"] == "WILD"
    assert "agri" in s["reason"].lower() or "stubble" in s["reason"].lower()
    assert s["conf"] == 0.85
    assert abs(sum(s["probs"].values()) - 1.0) < 1e-4


def test_emission_proxy_flare_rates_finite():
    from agnivani.physics.planck import emission_proxy, EMISSION_FACTORS

    # 1. Direct emission_proxy call
    res = emission_proxy("FLARE", frp_derived_MW=45.0, span_days=5.0, n_days=5)
    assert res.co2e_rate_tph > 0 and isinstance(res.co2e_rate_tph, float)
    assert res.black_carbon_rate_kgph > 0 and isinstance(res.black_carbon_rate_kgph, float)
    expected_co2e = round(45.0 * 3.6 * EMISSION_FACTORS["FLARE"]["co2e_kg_per_mj"], 4)
    expected_bc = round(45.0 * 3.6 * EMISSION_FACTORS["FLARE"]["bc_g_per_mj"], 4)
    assert res.co2e_rate_tph == expected_co2e
    assert res.black_carbon_rate_kgph == expected_bc

    # 2. Zero or negative FRP returns 0.0
    zero_res = emission_proxy("FLARE", frp_derived_MW=0.0)
    assert zero_res.co2e_rate_tph == 0.0
    assert zero_res.black_carbon_rate_kgph == 0.0


def test_emission_proxy_wild_uses_fire_factor():
    from agnivani.physics.planck import emission_proxy, EMISSION_FACTORS

    frp_test = 30.0
    wild_res = emission_proxy("WILD", frp_derived_MW=frp_test)
    flare_res = emission_proxy("FLARE", frp_derived_MW=frp_test)

    # Distinct factors between wildfire biomass and gas flare
    assert wild_res.co2e_rate_tph != flare_res.co2e_rate_tph
    assert wild_res.black_carbon_rate_kgph != flare_res.black_carbon_rate_kgph

    # Asserts exact biomass combustion factor calculations
    expected_wild_co2e = round(frp_test * 3.6 * EMISSION_FACTORS["WILD"]["co2e_kg_per_mj"], 4)
    expected_wild_bc = round(frp_test * 3.6 * EMISSION_FACTORS["WILD"]["bc_g_per_mj"], 4)
    assert wild_res.co2e_rate_tph == expected_wild_co2e
    assert wild_res.black_carbon_rate_kgph == expected_wild_bc


def test_emission_proxy_offshore_suppressed_emits_null(tmp_path):
    from agnivani.features.build import build_features
    from agnivani.geo.registry import load_facilities
    from agnivani.models.scorer import HeuristicScorer, CLASSES
    from agnivani.ingest.scheduler import build_records
    from agnivani.api.schemas import DetectionOut

    # Marine / sea cluster with high FRP but water landcover
    sea_cluster = pd.DataFrame([{
        "source_id": "SEA_EMIT_1", "centroid_lat": 8.34184, "centroid_lon": 77.54288,
        "n_hits": 2, "n_days": 1, "n_nights": 0, "night_frac": 0.0,
        "first_seen": pd.Timestamp("2026-08-31 08:28:00", tz="UTC"),
        "last_seen": pd.Timestamp("2026-08-31 08:28:00", tz="UTC"),
        "span_days": 1, "frp_mean": 45.0, "frp_max": 45.0, "frp_median": 45.0, "frp_cv": 0.0,
        "ti4_median": 335.0, "ti4_max": 335.0, "ti5_median": 298.0, "dT_median": 37.0, "ti4_std": 0.0,
        "local_solar_hour": 13.0, "pixel_area_m2": 375**2, "cluster_extent_m": 0.0, "fill_ratio": 1.0,
        "recurrence_gap_days": 0.0, "flare_score": 5.0, "frp_derived_MW": 45.0
    }])
    facs = load_facilities(tmp_path)
    feats = build_features(sea_cluster, facs)
    assert feats.iloc[0]["landcover_water"] == 1.0

    scorer = HeuristicScorer()
    scores = scorer.score(feats)
    records = build_records(pd.DataFrame(), sea_cluster, feats, scores)
    assert len(records) == 1
    rec = records[0]

    # Must be suppressed and emit null (None) emission rates and totals (don't invent pollution for the sea)
    assert rec["offshore_suppressed"] is True
    assert rec["co2e_rate_tph"] is None
    assert rec["black_carbon_rate_kgph"] is None
    assert rec["co2e_total_t"] is None

    # Preserves 5-class invariant and sums to 1.0
    assert rec["cls"] in CLASSES
    assert len(rec["probs"]) == 5
    assert abs(sum(rec["probs"].values()) - 1.0) < 1e-4

    # Validates with Pydantic DetectionOut schema
    wire_out = DetectionOut(**rec)
    assert wire_out.co2e_rate_tph is None
    assert wire_out.black_carbon_rate_kgph is None
    assert wire_out.co2e_total_t is None
    assert abs(sum(wire_out.probs.values()) - 1.0) < 1e-4


def test_emission_proxy_onshore_flare_wire_record(tmp_path):
    from agnivani.features.build import build_features
    from agnivani.geo.registry import load_facilities
    from agnivani.models.scorer import HeuristicScorer, CLASSES
    from agnivani.ingest.scheduler import build_records
    from agnivani.api.schemas import DetectionOut

    # Onshore flare cluster near Hazira
    flare_cluster = pd.DataFrame([{
        "source_id": "HAZ_FLARE_1", "centroid_lat": 21.10, "centroid_lon": 72.64,
        "n_hits": 15, "n_days": 5, "n_nights": 10, "night_frac": 0.67,
        "first_seen": pd.Timestamp("2026-08-27 18:00:00", tz="UTC"),
        "last_seen": pd.Timestamp("2026-09-01 19:00:00", tz="UTC"),
        "span_days": 5, "frp_mean": 50.0, "frp_max": 65.0, "frp_median": 48.0, "frp_cv": 0.2,
        "ti4_median": 350.0, "ti4_max": 365.0, "ti5_median": 293.0, "dT_median": 57.0, "ti4_std": 4.0,
        "local_solar_hour": 22.0, "pixel_area_m2": 375**2, "cluster_extent_m": 800.0, "fill_ratio": 1.0,
        "recurrence_gap_days": 1.0, "flare_score": 25.0, "frp_derived_MW": 50.0,
        "diurnal_shape": "FLAT_24H", "t_fire_K": 1650.0
    }])
    facs = load_facilities(tmp_path)
    feats = build_features(flare_cluster, facs)
    scorer = HeuristicScorer()
    scores = scorer.score(feats)
    records = build_records(pd.DataFrame(), flare_cluster, feats, scores)
    assert len(records) == 1
    rec = records[0]

    assert rec["offshore_suppressed"] is False
    assert rec["co2e_rate_tph"] is not None and rec["co2e_rate_tph"] > 0
    assert rec["black_carbon_rate_kgph"] is not None and rec["black_carbon_rate_kgph"] > 0
    assert rec["co2e_total_t"] is not None and rec["co2e_total_t"] > 0
    # Expected cumulative total over 5 days: rate * 5 * 24
    assert rec["co2e_total_t"] == round(rec["co2e_rate_tph"] * 5 * 24.0, 3)

    # 5-class invariant and prob sum
    assert rec["cls"] == "FLARE"
    assert len(rec["probs"]) == 5
    assert abs(sum(rec["probs"].values()) - 1.0) < 1e-4

    wire_out = DetectionOut(**rec)
    assert wire_out.co2e_rate_tph == rec["co2e_rate_tph"]
    assert wire_out.black_carbon_rate_kgph == rec["black_carbon_rate_kgph"]
    assert wire_out.co2e_total_t == rec["co2e_total_t"]


def test_no_hallucinated_numbers_guard():
    from agnivani.narrative.reason import (
        build_evidence,
        validate_no_hallucinated_numbers,
        generate_template_reason,
    )

    evidence = build_evidence(
        cls="FLARE",
        conf=0.92,
        lo=0.85,
        hi=0.95,
        facility_name="Jamnagar Refinery",
        dist_facility_m=450.0,
        t_fire_K=1847.0,
        frp_max=62.1,
        n_days=5,
        night_frac=0.8,
        diurnal_shape="FLAT_24H",
        landcover_class="built",
        co2e_rate_tph=12.34,
        offshore_suppressed=False,
    )

    # 1. Template narrative passes guard
    template_narrative, cited_rule = generate_template_reason(evidence)
    assert cited_rule == "CPCB-FLARE-PERMIT"
    assert validate_no_hallucinated_numbers(template_narrative, evidence) is True

    # 2. Grounded narrative with allowed numbers passes
    grounded = (
        "FLARE alert confirmed with 0.92 confidence [0.85-0.95] driven by "
        "retrieved temperature of 1847 K and persistent recurrence over 5 days; "
        "implicates CPCB flare-permit standard; audit plant operational logs."
    )
    assert validate_no_hallucinated_numbers(grounded, evidence) is True

    # 3. Hallucinated arbitrary number (e.g. 9999 or 42) must fail guard
    hallucinated = (
        "FLARE alert confirmed with 0.92 confidence [0.85-0.95] driven by "
        "retrieved temperature of 1847 K and 9999 MW FRP; "
        "implicates CPCB flare-permit standard; audit plant operational logs."
    )
    assert validate_no_hallucinated_numbers(hallucinated, evidence) is False

    # 4. Hallucinated year or section number in regulation must fail guard
    hallucinated_year = (
        "FLARE alert confirmed with 0.92 confidence [0.85-0.95] driven by "
        "retrieved temperature of 1847 K; implicates CPCB Rule 2016; audit plant logs."
    )
    assert validate_no_hallucinated_numbers(hallucinated_year, evidence) is False


def test_generated_reason_fields_and_cited_rule(tmp_path):
    from agnivani.features.build import build_features, FEATURES, FORBIDDEN
    from agnivani.geo.registry import load_facilities
    from agnivani.models.scorer import HeuristicScorer, CLASSES
    from agnivani.ingest.scheduler import build_records
    from agnivani.api.schemas import DetectionOut
    from agnivani.narrative.reason import validate_no_hallucinated_numbers, build_evidence

    clusters = pd.DataFrame([
        {
            "source_id": "TEST_FLARE", "centroid_lat": 21.10, "centroid_lon": 72.64,
            "n_hits": 15, "n_days": 5, "n_nights": 10, "night_frac": 0.67,
            "first_seen": pd.Timestamp("2026-08-27 18:00:00", tz="UTC"),
            "last_seen": pd.Timestamp("2026-09-01 19:00:00", tz="UTC"),
            "span_days": 5, "frp_mean": 50.0, "frp_max": 65.0, "frp_median": 48.0, "frp_cv": 0.2,
            "ti4_median": 350.0, "ti4_max": 365.0, "ti5_median": 293.0, "dT_median": 57.0, "ti4_std": 4.0,
            "local_solar_hour": 22.0, "pixel_area_m2": 375**2, "cluster_extent_m": 800.0, "fill_ratio": 1.0,
            "recurrence_gap_days": 1.0, "flare_score": 25.0, "frp_derived_MW": 50.0,
            "diurnal_shape": "FLAT_24H", "t_fire_K": 1650.0
        },
        {
            "source_id": "TEST_SEA", "centroid_lat": 8.34184, "centroid_lon": 77.54288,
            "n_hits": 1, "n_days": 1, "n_nights": 0, "night_frac": 0.0,
            "first_seen": pd.Timestamp("2026-08-31 08:28:00", tz="UTC"),
            "last_seen": pd.Timestamp("2026-08-31 08:28:00", tz="UTC"),
            "span_days": 1, "frp_mean": 8.3, "frp_max": 8.3, "frp_median": 8.3, "frp_cv": 0.0,
            "ti4_median": 328.0, "ti4_max": 328.0, "ti5_median": 302.56, "dT_median": 25.44, "ti4_std": 0.0,
            "local_solar_hour": 13.0, "pixel_area_m2": 375**2, "cluster_extent_m": 0.0, "fill_ratio": 1.0,
            "recurrence_gap_days": 0.0, "flare_score": 5.0
        }
    ])
    facs = load_facilities(tmp_path)
    feats = build_features(clusters, facs)
    scorer = HeuristicScorer()
    scores = scorer.score(feats)
    records = build_records(pd.DataFrame(), clusters, feats, scores)

    assert len(records) == 2
    for rec in records:
        # 1. Presence of narrative fields
        assert "reason" in rec and isinstance(rec["reason"], str) and len(rec["reason"]) > 0
        assert "reason_template" in rec and isinstance(rec["reason_template"], str) and len(rec["reason_template"]) > 0
        assert "cited_rule" in rec and isinstance(rec["cited_rule"], str) and len(rec["cited_rule"]) > 0

        # 2. Exactly ONE sentence (ends with ., no unjoined multiple sentences)
        assert rec["reason"].endswith(".")
        assert rec["reason"].count(". ") == 0

        # 3. Anti-hallucination guard test on record reason
        ev = build_evidence(
            cls=rec["cls"],
            conf=rec["conf"],
            lo=rec["lo"],
            hi=rec["hi"],
            facility_name=rec.get("facility_name"),
            facility_sector=rec.get("facility_sector"),
            dist_facility_m=rec.get("dist_facility_m"),
            t_fire_K=rec.get("temp_K"),
            frp_max=rec.get("frp_max_MW", 0.0),
            n_days=rec.get("n_days", 1),
            night_frac=rec.get("night_frac", 0.0),
            diurnal_shape=rec.get("diurnal_shape"),
            co2e_rate_tph=rec.get("co2e_rate_tph"),
            offshore_suppressed=rec.get("offshore_suppressed", False),
        )
        assert validate_no_hallucinated_numbers(rec["reason"], ev) is True

        # 4. Valid wire schema contract
        wire = DetectionOut(**rec)
        assert wire.reason == rec["reason"]
        assert wire.reason_template == rec["reason_template"]
        assert wire.cited_rule == rec["cited_rule"]

        # 5. 5-class invariant and prob sum
        assert rec["cls"] in CLASSES
        assert len(rec["probs"]) == 5
        assert abs(sum(rec["probs"].values()) - 1.0) < 1e-4

    # 6. Coordinate leakage invariant
    assert not (set(FEATURES) & FORBIDDEN)



