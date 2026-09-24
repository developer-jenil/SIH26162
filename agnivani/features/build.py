"""Leakage-safe source feature matrix construction."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from agnivani.geo.registry import nearest_facility
from agnivani.physics.planck import dozier

SECTORS = ["STEEL","CEMENT","COAL","POWER","REFI_GAS","FERTILIZER","OTHER","UNKNOWN"]
LANDCOVERS = ["forest","grassland","shrub","cropland","built","water","other","unknown"]
DIURNAL_SHAPES = ["FLAT_24H","SPIKE_DECAY","EVENING_BURST","DAYTIME_ONLY","SPARSE"]
FEATURES = [
 "t_fire_K","frac","frp_derived_MW","dT","ti4_ti5_ratio","log1p_frp_max","local_hour_sin","local_hour_cos","is_night",
 "n_days","n_nights","night_frac","span_days","hits_per_day","recurrence_gap_days","frp_cv","ti4_std","cluster_extent_m",
 "fill_ratio","log1p_dist_nearest_facility_m","dist_nearest_settlement_m",
] + [f"sector_{x}" for x in SECTORS] + [f"landcover_{x}" for x in LANDCOVERS] + [f"diurnal_{x}" for x in DIURNAL_SHAPES] + ["diurnal_shape"]
FORBIDDEN = {"lat","lon","latitude","longitude","centroid_lat","centroid_lon","block_id","lat_cell","lon_cell","facility_lat","facility_lon"}

CONTEXT_COLUMNS = [
    "source_id",
    "block_id",
    "facility_name",
    "facility_sector",
    "dist_facility_m",
    "landcover_class",
    "landcover_status",
    "state",
    "district",
]


def canonical_frame(features_df: pd.DataFrame) -> pd.DataFrame:
    """Return the single frame that scorers must receive: FEATURES + CONTEXT_COLUMNS.

    Slicing to FEATURES alone silently breaks the HeuristicScorer's context-dependent rules.
    """
    needed_cols = [c for c in CONTEXT_COLUMNS if c in features_df.columns]
    feat_cols = [c for c in FEATURES if c in features_df.columns]
    dynamic_cols = [c for c in ["diurnal_hist", "retrieval_flags"] if c in features_df.columns]
    ordered_cols = list(dict.fromkeys(needed_cols + feat_cols + dynamic_cols))
    return features_df[ordered_cols].copy()


def spatial_block_id(lat: float, lon: float, size_deg: float = 2.0) -> str:
    return f"{math.floor(lat/size_deg)}_{math.floor(lon/size_deg)}"


def build_features(sources_df: pd.DataFrame, facilities_gdf, landcover=None, lc_dict=None) -> pd.DataFrame:
    if landcover is None and lc_dict is not None:
        landcover = lc_dict
    from agnivani.geo.landcover import resolve_landcover
    from agnivani.geo.cluster import compute_diurnal_shape
    rows=[]
    for _, s in sources_df.iterrows():
        facility, distance = nearest_facility(facilities_gdf, s.centroid_lat, s.centroid_lon)
        t_bg_val = s.get("t_bg_K") if pd.notna(s.get("t_bg_K")) else None
        retrieval = dozier(float(s.ti4_median), float(s.ti5_median), float(s.get("pixel_area_m2",375**2)), t_bg_K=t_bg_val)
        sector = facility.sector if facility else "UNKNOWN"
        raw_lc = s.get("landcover_class")
        if (raw_lc is None or pd.isna(raw_lc) or str(raw_lc).lower().strip() in ("unknown", "nan", "none", "")) and landcover is not None:
            if isinstance(landcover, dict):
                raw_lc = landcover.get(s.source_id) or landcover.get((s.centroid_lat, s.centroid_lon)) or landcover.get((round(s.centroid_lat, 3), round(s.centroid_lon, 3)))
            elif isinstance(landcover, pd.Series):
                raw_lc = landcover.get(s.source_id)
        if raw_lc is None or pd.isna(raw_lc) or str(raw_lc).lower().strip() in ("unknown", "nan", "none", ""):
            raw_lc = resolve_landcover(s.centroid_lat, s.centroid_lon)
        raw_lc = str(raw_lc).lower().strip() if raw_lc is not None else ""
        lc = raw_lc if raw_lc in LANDCOVERS else "other"
        hour=float(s.get("local_solar_hour",12)); dist = float(distance) if np.isfinite(distance) else 1_000_000.

        hist = s.get("diurnal_hist")
        if hist is None or not isinstance(hist, (list, np.ndarray)) or len(hist) != 24:
            hist = [0.0] * 24
            bin_idx = int(math.floor(hour)) % 24
            hist[bin_idx] = 1.0
        else:
            hist = [float(x) for x in hist]

        shape = s.get("diurnal_shape")
        if not shape or shape not in DIURNAL_SHAPES:
            shape = compute_diurnal_shape(hist, n_hits=int(s.get("n_hits", 1)), night_frac=float(s.get("night_frac", 0.0)))

        row={"source_id":s.source_id,"block_id":spatial_block_id(s.centroid_lat,s.centroid_lon),"facility_name":facility.name if facility else None,
             "facility_sector":facility.sector if facility else None,"dist_facility_m":float(distance) if np.isfinite(distance) else None,
             "state":(facility.state or None) if facility else None,"district":(facility.district or None) if facility else None,
             "t_fire_K":s.get("t_fire_K") if pd.notna(s.get("t_fire_K")) else retrieval.t_fire_K,"frac":s.get("frac") if pd.notna(s.get("frac")) else (retrieval.frac if retrieval.converged else None),"frp_derived_MW":s.get("frp_derived_MW") if pd.notna(s.get("frp_derived_MW")) else retrieval.frp_derived_MW,
             "dT":float(s.dT_median),"ti4_ti5_ratio":float(s.ti4_median/s.ti5_median),"log1p_frp_max":math.log1p(max(0,float(s.frp_max))),
             "local_hour_sin":math.sin(2*math.pi*hour/24),"local_hour_cos":math.cos(2*math.pi*hour/24),"is_night":float(s.night_frac>=.5),
             "n_days":int(s.n_days),"n_nights":int(s.n_nights),"night_frac":float(s.night_frac),"span_days":int(s.span_days),
             "hits_per_day":float(s.n_hits/max(1,s.n_days)),"recurrence_gap_days":float(s.recurrence_gap_days),"frp_cv":float(s.frp_cv),
             "ti4_std":float(s.ti4_std),"cluster_extent_m":float(s.cluster_extent_m),"fill_ratio":float(s.fill_ratio),
             "log1p_dist_nearest_facility_m":math.log1p(dist),"dist_nearest_settlement_m":float(s.get("dist_nearest_settlement_m",1_000_000)),
             "landcover_class":lc,"landcover_status":s.get("landcover_status", "unavailable"),"retrieval_flags":retrieval.flags,
             "diurnal_hist":hist,"diurnal_shape":shape}
        row.update({f"sector_{x}":float(sector==x) for x in SECTORS}); row.update({f"landcover_{x}":float(lc==x) for x in LANDCOVERS})
        row.update({f"diurnal_{x}":float(shape==x) for x in DIURNAL_SHAPES})
        rows.append(row)
    result=pd.DataFrame(rows)
    assert not (set(FEATURES)&FORBIDDEN), "coordinate leakage in FEATURES"
    return result
