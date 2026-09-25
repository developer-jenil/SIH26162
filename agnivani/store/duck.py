"""Thread-safe DuckDB store and persistence helpers."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, threading
import duckdb, pandas as pd

import os

class DuckStore:
    def __init__(self, data_dir, read_only: bool | None = None):
        self.data_dir = Path(data_dir)
        (self.data_dir / "processed").mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if read_only is not None:
            self.read_only = read_only
        else:
            self.read_only = os.getenv("AGNIVANI_READONLY_DB", "").lower() in ("1", "true", "yes")
        db_path = str(self.data_dir / "agnivani.duckdb")
        try:
            self.conn = duckdb.connect(db_path, read_only=self.read_only)
        except Exception as exc:
            if not self.read_only and "already open" in str(exc).lower():
                self.read_only = True
                self.conn = duckdb.connect(db_path, read_only=True)
            else:
                raise
        if not self.read_only:
            self._ddl()
    def _ddl(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS detections (id VARCHAR PRIMARY KEY, payload JSON, ts TIMESTAMPTZ, cls VARCHAR, conf DOUBLE, severity VARCHAR, lat DOUBLE, lon DOUBLE)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS sources (id VARCHAR PRIMARY KEY, payload JSON)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS facilities (id VARCHAR PRIMARY KEY, payload JSON, sector VARCHAR)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS alerts (id VARCHAR PRIMARY KEY, payload JSON, dispatched_at TIMESTAMPTZ)")
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS pipeline_seq START 1")
        self.conn.execute("CREATE TABLE IF NOT EXISTS pipeline_log (id BIGINT PRIMARY KEY DEFAULT nextval('pipeline_seq'), ts TIMESTAMPTZ, stage VARCHAR, level VARCHAR, message VARCHAR, elapsed_ms BIGINT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS pipeline_runs (run_id VARCHAR PRIMARY KEY, ts TIMESTAMPTZ, filename VARCHAR, num_raw BIGINT, num_sources BIGINT, stages JSON, status VARCHAR, total_ms BIGINT)")
        for name in ("detections","sources","facilities","labelled"):
            path=self.data_dir/"processed"/f"{name}.parquet"
            if path.exists():
                escaped = str(path).replace("'", "''")
                self.conn.execute(f"CREATE OR REPLACE VIEW v_{name} AS SELECT * FROM read_parquet('{escaped}')")
    def query(self,sql,params=None):
        with self._lock:return self.conn.execute(sql,params or []).fetchdf()
    def log(self, stage, message, elapsed_ms=None, level="INFO"):
        if self.read_only:
            return
        with self._lock:
            self.conn.execute("INSERT INTO pipeline_log(ts,stage,level,message,elapsed_ms) VALUES (?,?,?,?,?)",[datetime.now(timezone.utc),stage,level,message,elapsed_ms])
    def upsert_detection(self, item):
        if self.read_only:
            return
        payload = json.dumps(item, default=str, separators=(",",":"))
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO detections VALUES (?,?,?,?,?,?,?,?)",[item["id"],payload,item["ts"],item["cls"],item["conf"],item["severity"],item["lat"],item["lon"]])
    def upsert_facility(self, item):
        if self.read_only:
            return
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO facilities VALUES (?,?,?)",[item["facility_id"],json.dumps(item,default=str),item["sector"]])
    def detections(self):
        return [json.loads(x) for x in self.query("SELECT payload FROM detections ORDER BY ts DESC").payload.tolist()]
    def record_pipeline_run(self, run_id: str, filename: str, num_raw: int, num_sources: int, stages: dict | list, status: str, total_ms: int):
        if self.read_only:
            return
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO pipeline_runs VALUES (?,?,?,?,?,?,?,?)",
                [run_id, datetime.now(timezone.utc), filename, int(num_raw), int(num_sources), json.dumps(stages, default=str), status, int(total_ms)]
            )
    def pipeline_runs(self, limit: int = 50):
        with self._lock:
            df = self.conn.execute("SELECT * FROM pipeline_runs ORDER BY ts DESC LIMIT ?", [limit]).fetchdf()
            if df.empty:
                return []
            runs = []
            for _, r in df.iterrows():
                st = r["stages"]
                if isinstance(st, str):
                    try: st = json.loads(st)
                    except Exception: pass
                runs.append({
                    "run_id": str(r["run_id"]),
                    "ts": pd.Timestamp(r["ts"]).to_pydatetime().astimezone(timezone.utc),
                    "filename": str(r["filename"]),
                    "num_raw": int(r["num_raw"]),
                    "num_sources": int(r["num_sources"]),
                    "stages": st,
                    "status": str(r["status"]),
                    "total_ms": int(r["total_ms"])
                })
            return runs
    def close(self):
        with self._lock:self.conn.close()

