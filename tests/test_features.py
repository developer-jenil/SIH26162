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
