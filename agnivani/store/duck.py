"""Thread-safe DuckDB store and persistence helpers."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, threading
import duckdb, pandas as pd

class DuckStore:
    def __init__(self,data_dir):
        self.data_dir=Path(data_dir); (self.data_dir/"processed").mkdir(parents=True,exist_ok=True)
        self._lock=threading.RLock(); self.conn=duckdb.connect(str(self.data_dir/"agnivani.duckdb")); self._ddl()
    def _ddl(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS detections (id VARCHAR PRIMARY KEY, payload JSON, ts TIMESTAMPTZ, cls VARCHAR, conf DOUBLE, severity VARCHAR, lat DOUBLE, lon DOUBLE)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS sources (id VARCHAR PRIMARY KEY, payload JSON)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS facilities (id VARCHAR PRIMARY KEY, payload JSON, sector VARCHAR)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS alerts (id VARCHAR PRIMARY KEY, payload JSON, dispatched_at TIMESTAMPTZ)")
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS pipeline_seq START 1")
        self.conn.execute("CREATE TABLE IF NOT EXISTS pipeline_log (id BIGINT PRIMARY KEY DEFAULT nextval('pipeline_seq'), ts TIMESTAMPTZ, stage VARCHAR, level VARCHAR, message VARCHAR, elapsed_ms BIGINT)")
        for name in ("detections","sources","facilities","labelled"):
            path=self.data_dir/"processed"/f"{name}.parquet"
            if path.exists():
                escaped = str(path).replace("'", "''")
                self.conn.execute(f"CREATE OR REPLACE VIEW v_{name} AS SELECT * FROM read_parquet('{escaped}')")
    def query(self,sql,params=None):
        with self._lock:return self.conn.execute(sql,params or []).fetchdf()
    def log(self,stage,message,elapsed_ms=None,level="INFO"):
        with self._lock:self.conn.execute("INSERT INTO pipeline_log(ts,stage,level,message,elapsed_ms) VALUES (?,?,?,?,?)",[datetime.now(timezone.utc),stage,level,message,elapsed_ms])
    def upsert_detection(self,item):
        payload=json.dumps(item,default=str,separators=(",",":"))
        with self._lock:self.conn.execute("INSERT OR REPLACE INTO detections VALUES (?,?,?,?,?,?,?,?)",[item["id"],payload,item["ts"],item["cls"],item["conf"],item["severity"],item["lat"],item["lon"]])
    def upsert_facility(self,item):
        with self._lock:self.conn.execute("INSERT OR REPLACE INTO facilities VALUES (?,?,?)",[item["facility_id"],json.dumps(item,default=str),item["sector"]])
    def detections(self): return [json.loads(x) for x in self.query("SELECT payload FROM detections ORDER BY ts DESC").payload.tolist()]
    def close(self):
        with self._lock:self.conn.close()
