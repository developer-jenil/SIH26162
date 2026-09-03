"""Backfill/reprocess loop and transformation into dashboard wire records."""
from __future__ import annotations
import asyncio,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import structlog
from agnivani.features.build import build_features
from agnivani.geo.cluster import cluster_sources
from agnivani.geo.registry import load_facilities
from agnivani.ingest.firms import FirmsClient,load_all

log=structlog.get_logger()
LABELS=["VIIRS INGEST","INDIA FILTER","SOURCE CLUSTER","PLANCK RETRIEVAL","REGISTRY JOIN","CLASSIFY"]

def _severity(cls,conf,frp):
    if conf>=.85 or frp>=50:return "CRITICAL"
    if conf>=.7 or frp>=20:return "HIGH"
    if conf>=.5 or frp>=5:return "MODERATE"
    return "LOW"

def _evidence(source,feature,score):
    values=[f"{source.n_hits} detections",f"centroid inside mainland",f"{source.n_days} days / {source.n_hits} hits",
            f"T={feature.t_fire_K:.0f} K" if pd.notna(feature.t_fire_K) else "retrieval unresolved",
            feature.facility_name or "no facility within 10 km",f"{score.cls} p={score.conf:.2f}"]
    return [{"stage":i,"label":label,"status":"warn" if i in (4,5) and "no " in values[i-1] else "ok","detail":values[i-1],"value":values[i-1],"ms":0} for i,label in enumerate(LABELS,1)]

def build_records(raw,sources,features,scores):
    records=[]
    for i,s in sources.reset_index(drop=True).iterrows():
        f,q=features.iloc[i],scores.iloc[i]; probs={k:round(float(v),4) for k,v in q.probs.items()}
        delta=round(1-sum(probs.values()),4); probs[q.cls]=round(probs[q.cls]+delta,4)
        top=[{"name":name,"value":float(value),"contribution":0.0} for name,value in q.top_features]
        records.append({"id":s.source_id,"lat":s.centroid_lat,"lon":s.centroid_lon,"cls":q.cls,"conf":q.conf,"probs":probs,"lo":q.lo,"hi":q.hi,
          "temp_K":None if pd.isna(f.t_fire_K) else f.t_fire_K,"bg_K":s.ti5_median,"frac":None if pd.isna(f.frac) else f.frac,
          "frp_MW":0 if pd.isna(f.frp_derived_MW) else f.frp_derived_MW,"frp_max_MW":s.frp_max,"area_m2":s.pixel_area_m2,
          "ts":pd.Timestamp(s.last_seen).to_pydatetime().astimezone(timezone.utc),"n_hits":s.n_hits,"n_days":s.n_days,"night_frac":s.night_frac,
          "facility_name":f.facility_name,"facility_sector":f.facility_sector,"dist_facility_m":f.dist_facility_m,"state":f.state,"district":f.district,
          "severity":_severity(q.cls,q.conf,s.frp_max),"reason":q.reason,"evidence":_evidence(s,f,q),"top_features":top})
    return records

async def process_once(app,fetch_days=1,fetch=True):
    start=time.perf_counter(); settings=app.state.settings; store=app.state.store
    if fetch: await FirmsClient(settings).fetch_range(fetch_days)
    raw=await asyncio.to_thread(load_all,settings.data_dir); store.log("VIIRS INGEST",f"normalised {len(raw)} mainland detections",int((time.perf_counter()-start)*1000))
    if raw.empty:return []
    sources=await asyncio.to_thread(cluster_sources,raw,settings.cluster_cell_deg)
    facilities=await asyncio.to_thread(load_facilities,settings.data_dir)
    features=await asyncio.to_thread(build_features,sources,facilities)
    scores=await asyncio.to_thread(app.state.scorer.score,features)
    records=build_records(raw,sources,features,scores)
    for item in records:store.upsert_detection(item)
    store.log("CLASSIFY",f"scored and stored {len(records)} sources",int((time.perf_counter()-start)*1000))
    for item in records:await app.state.broker.publish("detection",item)
    await app.state.broker.publish("ingest",{"detections":len(raw),"sources":len(records),"at":datetime.now(timezone.utc).isoformat()})
    return records

async def scheduler_loop(app):
    while True:
        try:await process_once(app,1,True)
        except asyncio.CancelledError:raise
        except Exception as exc:
            app.state.store.log("INGEST","poll failed; serving cached data",level="ERROR"); log.exception("poll_failed",error=str(exc))
        await asyncio.sleep(app.state.settings.poll_interval_seconds)
