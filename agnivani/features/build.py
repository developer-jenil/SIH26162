"""Leakage-safe source feature matrix construction."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from agnivani.geo.registry import nearest_facility
from agnivani.physics.planck import dozier

SECTORS = ["STEEL","CEMENT","COAL","POWER","REFI_GAS","FERTILIZER","OTHER","UNKNOWN"]
LANDCOVERS = ["forest","grassland","shrub","cropland","built","water","other","unknown"]
FEATURES = [
 "t_fire_K","frac","frp_derived_MW","dT","ti4_ti5_ratio","log1p_frp_max","local_hour_sin","local_hour_cos","is_night",
 "n_days","n_nights","night_frac","span_days","hits_per_day","recurrence_gap_days","frp_cv","ti4_std","cluster_extent_m",
 "fill_ratio","log1p_dist_nearest_facility_m","dist_nearest_settlement_m",
] + [f"sector_{x}" for x in SECTORS] + [f"landcover_{x}" for x in LANDCOVERS]
FORBIDDEN = {"lat","lon","latitude","longitude","centroid_lat","centroid_lon","block_id","lat_cell","lon_cell","facility_lat","facility_lon"}


def spatial_block_id(lat: float, lon: float, size_deg: float = 2.0) -> str:
    return f"{math.floor(lat/size_deg)}_{math.floor(lon/size_deg)}"


def build_features(sources_df: pd.DataFrame, facilities_gdf, landcover=None) -> pd.DataFrame:
    rows=[]
    for _, s in sources_df.iterrows():
        facility, distance = nearest_facility(facilities_gdf, s.centroid_lat, s.centroid_lon)
        retrieval = dozier(float(s.ti4_median), float(s.ti5_median), float(s.get("pixel_area_m2",375**2)))
        sector = facility.sector if facility else "UNKNOWN"
        lc = str(s.get("landcover_class", "unknown")).lower(); lc = lc if lc in LANDCOVERS else "other"
        hour=float(s.get("local_solar_hour",12)); dist = float(distance) if np.isfinite(distance) else 1_000_000.
        row={"source_id":s.source_id,"block_id":spatial_block_id(s.centroid_lat,s.centroid_lon),"facility_name":facility.name if facility else None,
             "facility_sector":facility.sector if facility else None,"dist_facility_m":float(distance) if np.isfinite(distance) else None,
             "state":(facility.state or None) if facility else None,"district":(facility.district or None) if facility else None,
             "t_fire_K":retrieval.t_fire_K,"frac":retrieval.frac if retrieval.converged else None,"frp_derived_MW":retrieval.frp_derived_MW,
             "dT":float(s.dT_median),"ti4_ti5_ratio":float(s.ti4_median/s.ti5_median),"log1p_frp_max":math.log1p(max(0,float(s.frp_max))),
             "local_hour_sin":math.sin(2*math.pi*hour/24),"local_hour_cos":math.cos(2*math.pi*hour/24),"is_night":float(s.night_frac>=.5),
             "n_days":int(s.n_days),"n_nights":int(s.n_nights),"night_frac":float(s.night_frac),"span_days":int(s.span_days),
             "hits_per_day":float(s.n_hits/max(1,s.n_days)),"recurrence_gap_days":float(s.recurrence_gap_days),"frp_cv":float(s.frp_cv),
             "ti4_std":float(s.ti4_std),"cluster_extent_m":float(s.cluster_extent_m),"fill_ratio":float(s.fill_ratio),
             "log1p_dist_nearest_facility_m":math.log1p(dist),"dist_nearest_settlement_m":float(s.get("dist_nearest_settlement_m",1_000_000)),
             "landcover_class":lc,"retrieval_flags":retrieval.flags}
        row.update({f"sector_{x}":float(sector==x) for x in SECTORS}); row.update({f"landcover_{x}":float(lc==x) for x in LANDCOVERS})
        rows.append(row)
    result=pd.DataFrame(rows)
    assert not (set(FEATURES)&FORBIDDEN), "coordinate leakage in FEATURES"
    return result
