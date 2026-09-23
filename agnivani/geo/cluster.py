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


def compute_diurnal_shape(hist: list[float], n_hits: int, night_frac: float = 0.0) -> str:
    """Classify 24-bin diurnal histogram into shape taxonomy.

    Taxonomy:
      - SPARSE: very few detections (n_hits <= 2)
      - FLAT_24H: uniform distribution across 24h or steady day & night burning
      - EVENING_BURST: concentrated in 16:00 - 20:59 local solar hour (crop stubble)
      - DAYTIME_ONLY: concentrated in 10:00 - 16:59 local solar hour (wildfire / vegetation)
      - SPIKE_DECAY: single sharp peak / sudden burst
    """
    if n_hits <= 2:
        return "SPARSE"

    peak_val = max(hist) if hist else 0.0
    peak_hour = int(np.argmax(hist)) if hist else 0

    # Shannon entropy: H = -sum(p * log(p)) for p > 0
    entropy = -sum(p * math.log(p) for p in hist if p > 0)
    norm_entropy = entropy / math.log(24.0) if len(hist) == 24 else 0.0

    # Key mass windows
    # Daytime mass (10:00 to 16:59, bins 10..16 inclusive)
    daytime_mass = sum(hist[10:17]) if len(hist) >= 17 else 0.0
    # Evening mass (16:00 to 20:59, bins 16..20 inclusive)
    evening_mass = sum(hist[16:21]) if len(hist) >= 21 else 0.0

    val_spread = peak_val - (min(hist) if hist else 0.0)

    # 1. 24H Flat / Uniform: spread is very small or high normalized entropy with active night
    if val_spread < 0.08 or (norm_entropy > 0.82 and night_frac >= 0.25 and peak_val < 0.20):
        return "FLAT_24H"

    # 2. Evening burst (stubble burning, typically 16-20h)
    if evening_mass >= 0.50 or (evening_mass >= 0.35 and 16 <= peak_hour <= 20 and daytime_mass < 0.50):
        return "EVENING_BURST"

    # 3. Daytime only (wildfires, 10-16h)
    if daytime_mass >= 0.50 or (daytime_mass >= 0.35 and 10 <= peak_hour <= 16 and evening_mass < 0.40):
        return "DAYTIME_ONLY"

    # 4. Spike & decay / single sharp burst
    if peak_val >= 0.25:
        return "SPIKE_DECAY"

    # Fallbacks
    if night_frac >= 0.35 and norm_entropy > 0.70:
        return "FLAT_24H"

    return "SPIKE_DECAY"


def cluster_sources(df: pd.DataFrame, cell_deg: float = 0.02) -> pd.DataFrame:
    columns = ["source_id","n_hits","n_days","n_nights","night_frac","first_seen","last_seen","span_days",
               "frp_mean","frp_max","frp_median","frp_cv","ti4_median","ti4_max","ti5_median","dT_median",
               "ti4_std","local_solar_hour","pixel_area_m2","cluster_extent_m","fill_ratio","recurrence_gap_days",
               "centroid_lat","centroid_lon","flare_score","diurnal_hist","diurnal_shape"]
    if df.empty: return pd.DataFrame(columns=columns)
    work = df.copy()
    work["lat_cell"] = np.floor(work.latitude / cell_deg).astype(int)
    work["lon_cell"] = np.floor(work.longitude / cell_deg).astype(int)
    work["dT"] = work.bright_ti4 - work.bright_ti5
    records = []
    for (la, lo), g in work.groupby(["lat_cell", "lon_cell"], sort=True):
        first, last = pd.to_datetime(g.acq_utc).min(), pd.to_datetime(g.acq_utc).max()
        mean, std = float(g.frp.mean()), float(g.frp.std(ddof=0))

        # Extract local solar hours for detections in cluster g
        if "local_solar_hour" in g.columns and g.local_solar_hour.notna().any():
            hours = g.local_solar_hour.dropna().to_numpy()
        elif "acq_utc" in g.columns and g.acq_utc.notna().any():
            lons = g.longitude.to_numpy()
            utc = pd.to_datetime(g.acq_utc)
            hours = ((utc.dt.hour + utc.dt.minute / 60.0 + lons / 15.0) % 24).to_numpy()
        elif "acq_time" in g.columns:
            lons = g.longitude.to_numpy() if "longitude" in g.columns else np.zeros(len(g))
            t_str = g.acq_time.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(4)
            h = pd.to_numeric(t_str.str[:2], errors="coerce").fillna(12.0)
            m = pd.to_numeric(t_str.str[2:], errors="coerce").fillna(0.0)
            hours = ((h + m / 60.0 + lons / 15.0) % 24).to_numpy()
        else:
            hours = np.full(len(g), 12.0)

        n_nights = int((g.daynight == "N").sum()) if "daynight" in g.columns else int(np.sum((hours < 6.0) | (hours >= 18.0)))
        night_frac = n_nights / len(g) if len(g) else 0.0

        counts = [0] * 24
        for hr in hours:
            b = int(math.floor(float(hr))) % 24
            counts[b] += 1
        n_h = len(hours)
        if n_h > 0:
            hist = [c / n_h for c in counts]
            hist[-1] = max(0.0, 1.0 - sum(hist[:-1]))
        else:
            hist = [1.0 / 24.0] * 24

        shape = compute_diurnal_shape(hist, n_hits=len(g), night_frac=night_frac)

        lsh = float(g.local_solar_hour.median()) if "local_solar_hour" in g.columns and g.local_solar_hour.notna().any() else float(np.median(hours))

        row = {"source_id": _source_id(la, lo), "n_hits": len(g), "n_days": int(pd.to_datetime(g.acq_date).nunique()),
               "n_nights": n_nights, "first_seen": first, "last_seen": last,
               "span_days": int((last.normalize() - first.normalize()).days) + 1, "frp_mean": mean,
               "frp_max": float(g.frp.max()), "frp_median": float(g.frp.median()), "frp_cv": std / mean if mean else 0.,
               "ti4_median": float(g.bright_ti4.median()), "ti4_max": float(g.bright_ti4.max()),
               "ti5_median": float(g.bright_ti5.median()), "dT_median": float(g.dT.median()),
               "ti4_std": float(g.bright_ti4.std(ddof=0)), "local_solar_hour": lsh,
               "pixel_area_m2": float(g.pixel_area_m2.median()), "cluster_extent_m": _extent(g), "fill_ratio": 1.0,
               "recurrence_gap_days": _recurrence(g), "centroid_lat": float(g.latitude.mean()), "centroid_lon": float(g.longitude.mean()),
               "night_frac": night_frac, "diurnal_hist": hist, "diurnal_shape": shape}
        row["flare_score"] = flare_score(row)
        records.append(row)
    return pd.DataFrame(records, columns=columns)
