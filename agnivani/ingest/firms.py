"""NASA FIRMS area client, CSV validation, and canonical normalisation."""
from __future__ import annotations
import asyncio
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
import re
import httpx
import numpy as np
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from agnivani.geo.india import india_mask

AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}/{end_date}"
KNOWN_FIRST_COLUMNS = {"latitude", "country_id", "acq_date"}

class FirmsResponseError(RuntimeError): pass
class RetryableFirmsError(RuntimeError): pass


class FirmsClient:
    def __init__(self, settings):
        self.settings = settings
        self.raw_dir = Path(settings.data_dir) / "raw" / "firms"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=2, max=60), retry=retry_if_exception_type((RetryableFirmsError, httpx.TransportError)))
    async def _fetch(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
        if response.status_code == 429 or response.status_code >= 500:
            raise RetryableFirmsError(f"FIRMS returned HTTP {response.status_code}")
        response.raise_for_status()
        first = next((line.strip() for line in response.text.splitlines() if line.strip()), "")
        first_col = first.lstrip("﻿").split(",", 1)[0].strip().lower()
        if first_col not in KNOWN_FIRST_COLUMNS:
            raise FirmsResponseError(f"FIRMS returned non-CSV response: {first[:120]}")
        return response.text

    async def fetch_range(self, days: int, end_date: date | None = None) -> list[Path]:
        if days < 1: raise ValueError("days must be at least 1")
        end_date = end_date or date.today()
        if self.settings.offline_mode:
            return sorted(self.raw_dir.glob("*.csv"))
        files, remaining, cursor = [], days, end_date
        bbox = ",".join(str(x) for x in self.settings.india_bbox)
        while remaining:
            chunk = min(5, remaining)
            for source in self.settings.firms_sources:
                target = self.raw_dir / f"{source}_{cursor.isoformat()}_{chunk}d.csv"
                if not target.exists():
                    url = AREA_URL.format(key=self.settings.firms_map_key, source=source, bbox=bbox, days=chunk, end_date=cursor.isoformat())
                    target.write_text(await self._fetch(url), encoding="utf-8")
                    await asyncio.sleep(1.1)
                files.append(target)
            cursor -= timedelta(days=chunk)
            remaining -= chunk
        return files


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df.copy()
    out = df.copy()
    out.columns = [re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_") for c in out.columns]
    required = {"latitude", "longitude", "bright_ti4", "bright_ti5", "acq_date", "acq_time"}
    missing = required - set(out.columns)
    if missing: raise ValueError(f"FIRMS CSV missing required columns: {sorted(missing)}")
    for column in ["latitude", "longitude", "bright_ti4", "bright_ti5", "scan", "track", "frp"]:
        if column not in out: out[column] = np.nan
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out = out.dropna(subset=["latitude", "longitude", "bright_ti4", "bright_ti5"])
    times = out.acq_time.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(4)
    out["acq_utc"] = pd.to_datetime(out.acq_date.astype(str) + " " + times.str[:2] + ":" + times.str[2:], utc=True, errors="coerce")
    out = out.dropna(subset=["acq_utc"])
    out["acq_date"] = out.acq_utc.dt.date
    out["satellite"] = out.get("satellite", pd.Series("UNKNOWN", index=out.index)).fillna("UNKNOWN").astype(str)
    out["instrument"] = out.get("instrument", pd.Series("VIIRS", index=out.index)).fillna("VIIRS").astype(str)
    out["daynight"] = out.get("daynight", pd.Series("D", index=out.index)).fillna("D").astype(str).str.upper().str[0].where(lambda s: s.isin(["D","N"]), "D")
    out["local_solar_hour"] = (out.acq_utc.dt.hour + out.acq_utc.dt.minute / 60 + out.longitude / 15) % 24
    area = out.scan * out.track
    # FIRMS VIIRS scan/track values are kilometres.
    out["pixel_area_m2"] = np.where(area.notna() & (area > 0), area * 1_000_000, 375 ** 2)
    out = out.loc[india_mask(out.longitude.to_numpy(), out.latitude.to_numpy())]
    return out.drop_duplicates(["latitude", "longitude", "acq_utc", "satellite"]).reset_index(drop=True)


def load_all(data_dir: Path | str) -> pd.DataFrame:
    paths = sorted((Path(data_dir) / "raw" / "firms").glob("*.csv"))
    frames = []
    for path in paths:
        try: frames.append(pd.read_csv(path))
        except (pd.errors.EmptyDataError, UnicodeDecodeError): continue
    return normalise(pd.concat(frames, ignore_index=True)) if frames else pd.DataFrame()
