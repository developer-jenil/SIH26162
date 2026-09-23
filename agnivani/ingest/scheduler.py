"""Backfill/reprocess loop and transformation into dashboard wire records."""
from __future__ import annotations
import asyncio,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
import structlog
from agnivani.features.build import build_features
from agnivani.geo.cluster import cluster_sources
from agnivani.geo.registry import load_facilities
from agnivani.ingest.firms import FirmsClient,load_all
from agnivani.physics.planck import emission_proxy
from agnivani.narrative.reason import build_evidence, generate_reason

log=structlog.get_logger()
LABELS=["VIIRS INGEST","INDIA FILTER","SOURCE CLUSTER","PLANCK RETRIEVAL","REGISTRY JOIN","CLASSIFY"]

def _severity(cls,conf,frp,offshore_suppressed=False):
    if offshore_suppressed:return "LOW"
    if conf>=.85 or frp>=50:return "CRITICAL"
    if conf>=.7 or frp>=20:return "HIGH"
    if conf>=.5 or frp>=5:return "MODERATE"
    return "LOW"

def _evidence(source,feature,score):
    values=[f"{source.n_hits} detections",f"centroid inside mainland",f"{source.n_days} days / {source.n_hits} hits",
            f"T={feature.t_fire_K:.0f} K" if pd.notna(feature.t_fire_K) else "retrieval unresolved",
            feature.facility_name or "no facility within 10 km",f"{score.cls} p={score.conf:.2f}"]
    return [{"stage":i,"label":label,"status":"warn" if i in (4,5) and "no " in values[i-1] else "ok","detail":values[i-1],"value":values[i-1],"ms":0} for i,label in enumerate(LABELS,1)]

def build_records(raw,sources,features,scores,settings=None):
    records=[]
    for i,s in sources.reset_index(drop=True).iterrows():
        f,q=features.iloc[i],scores.iloc[i]; probs={k:round(float(v),4) for k,v in q.probs.items()}
        delta=round(1-sum(probs.values()),4); probs[q.cls]=round(probs[q.cls]+delta,4)
        top=[{"name":name,"value":float(value),"contribution":0.0} for name,value in q.top_features]
        is_suppressed = bool(
            q.get("offshore_suppressed")
            or (f.get("landcover_water") == 1.0)
            or ((f.facility_name is None or pd.isna(f.facility_name)) and (f.dist_facility_m is None or pd.isna(f.dist_facility_m) or f.dist_facility_m > 25000) and s.frp_max < 5)
        )
        conf = min(q.conf, 0.10) if is_suppressed else q.conf
        severity = _severity(q.cls, conf, s.frp_max, offshore_suppressed=is_suppressed)
        d_hist = s.get("diurnal_hist") if ("diurnal_hist" in s and s.get("diurnal_hist") is not None) else f.get("diurnal_hist")
        d_shape = s.get("diurnal_shape") if ("diurnal_shape" in s and s.get("diurnal_shape") is not None) else f.get("diurnal_shape")
        if isinstance(d_hist, (list, np.ndarray)):
            d_hist = [float(x) for x in d_hist]
        else:
            d_hist = None

        if is_suppressed:
            co2e_rate_tph = None
            black_carbon_rate_kgph = None
            co2e_total_t = None
        else:
            frp_val = f.get("frp_derived_MW") if (pd.notna(f.get("frp_derived_MW")) and f.get("frp_derived_MW") > 0) else s.get("frp_max", 0.0)
            if frp_val is None or pd.isna(frp_val):
                frp_val = 0.0
            frp_val = float(frp_val)
            span_d = float(s.get("span_days", 1.0)) if pd.notna(s.get("span_days")) else 1.0
            n_d = int(s.get("n_days", 1)) if pd.notna(s.get("n_days")) else 1
            ep = emission_proxy(q.cls, frp_val, span_d, n_d)
            co2e_rate_tph = round(ep.co2e_rate_tph, 4)
            black_carbon_rate_kgph = round(ep.black_carbon_rate_kgph, 4)
            co2e_total_t = round(co2e_rate_tph * max(1.0, span_d) * 24.0, 3)

        lc_class = f.get("landcover_class") if hasattr(f, "get") else getattr(f, "landcover_class", None)
        evidence_dict = build_evidence(
            cls=q.cls,
            conf=conf,
            lo=q.lo,
            hi=q.hi,
            facility_name=f.facility_name,
            facility_sector=f.facility_sector,
            dist_facility_m=f.dist_facility_m,
            t_fire_K=f.t_fire_K,
            frp_max=s.frp_max,
            n_days=s.n_days,
            night_frac=s.night_frac,
            diurnal_shape=str(d_shape) if d_shape else None,
            landcover_class=lc_class,
            co2e_rate_tph=co2e_rate_tph,
            offshore_suppressed=is_suppressed,
        )
        reason, reason_template, cited_rule = generate_reason(evidence_dict, settings=settings)

        records.append({"id":s.source_id,"lat":s.centroid_lat,"lon":s.centroid_lon,"cls":q.cls,"conf":conf,"probs":probs,"lo":q.lo,"hi":q.hi,
          "temp_K":None if pd.isna(f.t_fire_K) else f.t_fire_K,"bg_K":s.ti5_median,"frac":None if pd.isna(f.frac) else f.frac,
          "frp_MW":0 if pd.isna(f.frp_derived_MW) else f.frp_derived_MW,"frp_max_MW":s.frp_max,"area_m2":s.pixel_area_m2,
          "ts":pd.Timestamp(s.last_seen).to_pydatetime().astimezone(timezone.utc),"n_hits":s.n_hits,"n_days":s.n_days,"night_frac":s.night_frac,
          "facility_name":f.facility_name,"facility_sector":f.facility_sector,"dist_facility_m":f.dist_facility_m,"state":f.state,"district":f.district,
          "severity":severity,"reason":reason,"reason_template":reason_template,"cited_rule":cited_rule,
          "offshore_suppressed":is_suppressed,"evidence":_evidence(s,f,q),"top_features":top,
          "diurnal_hist":d_hist,"diurnal_shape":str(d_shape) if d_shape else None,
          "co2e_rate_tph":co2e_rate_tph,"black_carbon_rate_kgph":black_carbon_rate_kgph,"co2e_total_t":co2e_total_t})
    return records

async def process_once(app,fetch_days=1,fetch=True):
    start=time.perf_counter(); settings=app.state.settings; store=app.state.store
    if fetch: await FirmsClient(settings).fetch_range(fetch_days)
    raw=await asyncio.to_thread(load_all,settings.data_dir); store.log("VIIRS INGEST",f"normalised {len(raw)} mainland detections",int((time.perf_counter()-start)*1000))
    if raw.empty:return []
    sources=await asyncio.to_thread(cluster_sources,raw,settings.cluster_cell_deg)
    facilities=await asyncio.to_thread(load_facilities,settings.data_dir)
    from agnivani.geo.landcover import resolve_landcover_batch
    lc_dict=await asyncio.to_thread(resolve_landcover_batch,sources,settings.data_dir)
    features=await asyncio.to_thread(build_features,sources,facilities,lc_dict)
    scores=await asyncio.to_thread(app.state.scorer.score,features)
    records=build_records(raw,sources,features,scores,settings=settings)
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
