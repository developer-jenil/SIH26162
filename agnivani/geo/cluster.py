"""Persistent-source aggregation on a deterministic ~2 km grid."""
from __future__ import annotations
import hashlib
import math
import numpy as np
import pandas as pd


def flare_score(row) -> float:
    return float(row["span_days"] * .6 + row["n_days"] * 3 + row["n_nights"] * 1.2 +
                 math.log1p(max(0, row["frp_max"])) * 2 + (4 if row["ti4_median"] > 320 else 0))


def _source_id(lat_cell: int, lon_cell: int) -> str:
    digest = hashlib.md5(f"{lat_cell}:{lon_cell}".encode(), usedforsecurity=False).hexdigest()[:8].upper()
    return f"AV-{digest}"


def _extent(group: pd.DataFrame) -> float:
    if len(group) < 2: return 0.0
    lat, lon = group.latitude.to_numpy(), group.longitude.to_numpy()
    dy = (lat[:, None] - lat) * 111_000
    dx = (lon[:, None] - lon) * 111_000 * np.cos(np.radians(np.mean(lat)))
    return float(np.sqrt(dx * dx + dy * dy).max())


def _recurrence(group: pd.DataFrame) -> float:
    days = pd.DatetimeIndex(pd.to_datetime(group.acq_date).unique()).sort_values()
    return float(np.median(days.to_series().diff().dropna().dt.total_seconds() / 86400)) if len(days) > 1 else 0.0


def cluster_sources(df: pd.DataFrame, cell_deg: float = 0.02) -> pd.DataFrame:
    columns = ["source_id","n_hits","n_days","n_nights","night_frac","first_seen","last_seen","span_days",
               "frp_mean","frp_max","frp_median","frp_cv","ti4_median","ti4_max","ti5_median","dT_median",
               "ti4_std","local_solar_hour","pixel_area_m2","cluster_extent_m","fill_ratio","recurrence_gap_days",
               "centroid_lat","centroid_lon","flare_score"]
    if df.empty: return pd.DataFrame(columns=columns)
    work = df.copy()
    work["lat_cell"] = np.floor(work.latitude / cell_deg).astype(int)
    work["lon_cell"] = np.floor(work.longitude / cell_deg).astype(int)
    work["dT"] = work.bright_ti4 - work.bright_ti5
    records = []
    for (la, lo), g in work.groupby(["lat_cell", "lon_cell"], sort=True):
        first, last = pd.to_datetime(g.acq_utc).min(), pd.to_datetime(g.acq_utc).max()
        mean, std = float(g.frp.mean()), float(g.frp.std(ddof=0))
        row = {"source_id": _source_id(la, lo), "n_hits": len(g), "n_days": int(pd.to_datetime(g.acq_date).nunique()),
               "n_nights": int((g.daynight == "N").sum()), "first_seen": first, "last_seen": last,
               "span_days": int((last.normalize() - first.normalize()).days) + 1, "frp_mean": mean,
               "frp_max": float(g.frp.max()), "frp_median": float(g.frp.median()), "frp_cv": std / mean if mean else 0.,
               "ti4_median": float(g.bright_ti4.median()), "ti4_max": float(g.bright_ti4.max()),
               "ti5_median": float(g.bright_ti5.median()), "dT_median": float(g.dT.median()),
               "ti4_std": float(g.bright_ti4.std(ddof=0)), "local_solar_hour": float(g.local_solar_hour.median()),
               "pixel_area_m2": float(g.pixel_area_m2.median()), "cluster_extent_m": _extent(g), "fill_ratio": 1.0,
               "recurrence_gap_days": _recurrence(g), "centroid_lat": float(g.latitude.mean()), "centroid_lon": float(g.longitude.mean())}
        row["night_frac"] = row["n_nights"] / row["n_hits"]
        row["flare_score"] = flare_score(row)
        records.append(row)
    return pd.DataFrame(records, columns=columns)
