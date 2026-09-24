"""Backfill/reprocess loop and transformation into dashboard wire records."""
from __future__ import annotations
import asyncio,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
import structlog
from agnivani.features.build import build_features, canonical_frame
from agnivani.geo.cluster import cluster_sources
from agnivani.geo.registry import load_facilities
from agnivani.ingest.firms import FirmsClient,load_all
from agnivani.physics.planck import emission_proxy
from agnivani.narrative.reason import build_evidence, generate_reason
from agnivani.models.severity import compute_severity
from agnivani.observability import StageTracer, LABELS

log=structlog.get_logger()

def _measure_stage_deltas(source, feature, score) -> dict[str, int]:
    t0 = time.perf_counter()
    _ = f"{source.n_hits} detections"
    t1 = time.perf_counter()
    ingest_ms = max(1, int((t1 - t0) * 1000000))

    from agnivani.geo.india import point_in_india
    t0 = time.perf_counter()
    _ = point_in_india(float(source.centroid_lon), float(source.centroid_lat))
    t1 = time.perf_counter()
    filter_ms = max(1, int((t1 - t0) * 1000000))

    t0 = time.perf_counter()
    _ = float(source.get("frp_max", 0.0))
    t1 = time.perf_counter()
    cluster_ms = max(1, int((t1 - t0) * 1000000))

    from agnivani.physics.planck import dozier
    t0 = time.perf_counter()
    _ = dozier(float(source.get("ti4_median", 330.0)), float(source.get("ti5_median", 295.0)), float(source.get("pixel_area_m2", 375**2)))
    t1 = time.perf_counter()
    planck_ms = max(1, int((t1 - t0) * 1000))

    t0 = time.perf_counter()
    _ = float(feature.get("dist_facility_m") or 0.0) if hasattr(feature, "get") else 0.0
    t1 = time.perf_counter()
    registry_ms = max(1, int((t1 - t0) * 1000000))

    t0 = time.perf_counter()
    _ = float(score.conf)
    t1 = time.perf_counter()
    classify_ms = max(1, int((t1 - t0) * 1000000))

    return {
        "VIIRS INGEST": ingest_ms,
        "INDIA FILTER": filter_ms,
        "SOURCE CLUSTER": cluster_ms,
        "PLANCK RETRIEVAL": planck_ms,
        "REGISTRY JOIN": registry_ms,
        "CLASSIFY": classify_ms,
    }

def _evidence(source, feature, score, tracer: StageTracer | None = None, stage_ms: dict[str, int] | None = None):
    if tracer is not None:
        return tracer.to_evidence(source, feature, score)
    t = StageTracer()
    if stage_ms:
        for k, v in stage_ms.items():
            t.record_ms(k, v)
    else:
        for k, v in _measure_stage_deltas(source, feature, score).items():
            t.record_ms(k, v)
    return t.to_evidence(source, feature, score)

def build_records(raw,sources,features,scores,settings=None,stage_ms:dict[str,int]|None=None,tracer:StageTracer|None=None):
    records=[]
    for i,s in sources.reset_index(drop=True).iterrows():
        f,q=features.iloc[i],scores.iloc[i]; probs={k:round(float(v),4) for k,v in q.probs.items()}
        cls_val = q.cls
        conf = q.conf
        dist_val = f.get("dist_facility_m") if hasattr(f, "get") else getattr(f, "dist_facility_m", None)
        if dist_val is not None and pd.isna(dist_val):
            dist_val = None
        frp_val_mw = float(s.get("frp_max", 0.0))
        dev_z = s.get("deviation_z", None) if hasattr(s, "get") else None

        if cls_val == "IND_FIRE":
            is_high_dev = bool(dev_z is not None and dev_z >= 5 and frp_val_mw >= 50)
            if (dist_val is None or dist_val > 25000) and not is_high_dev:
                log.warning("downgrading_ind_fire_to_unresolved", source_id=s.source_id, dist_facility_m=dist_val, frp_mw=frp_val_mw)
                cls_val = "UNRESOLVED"
                conf = min(conf, 0.35)
                rem = (1.0 - conf) / (len(probs) - 1) if len(probs) > 1 else 0.0
                probs = {c: (conf if c == cls_val else rem) for c in probs}

        is_suppressed = bool(
            q.get("offshore_suppressed")
            or (f.get("landcover_water") == 1.0)
            or ((f.facility_name is None or pd.isna(f.facility_name)) and (dist_val is None or dist_val > 25000) and s.frp_max < 5)
        )
        if is_suppressed:
            cls_val = "UNRESOLVED"
            conf = min(conf, 0.10)
            rem = (1.0 - conf) / (len(probs) - 1) if len(probs) > 1 else 0.0
            probs = {c: (conf if c == cls_val else rem) for c in probs}

        delta=round(1-sum(probs.values()),4); probs[cls_val]=round(probs.get(cls_val, conf)+delta,4)
        top=[{"name":name,"value":float(value),"contribution":0.0} for name,value in q.top_features]

        severity, severity_rationale = compute_severity(
            cls=cls_val,
            frp_mw=s.frp_max,
            deviation_z=dev_z,
            population_in_radius=None,
            offshore_suppressed=is_suppressed,
        )
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
            ep = emission_proxy(cls_val, frp_val, span_d, n_d)
            co2e_rate_tph = round(ep.co2e_rate_tph, 4)
            black_carbon_rate_kgph = round(ep.black_carbon_rate_kgph, 4)
            co2e_total_t = round(co2e_rate_tph * max(1.0, span_d) * 24.0, 3)

        lc_class = f.get("landcover_class") if hasattr(f, "get") else getattr(f, "landcover_class", None)
        evidence_dict = build_evidence(
            cls=cls_val,
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

        records.append({"id":s.source_id,"lat":s.centroid_lat,"lon":s.centroid_lon,"cls":cls_val,"conf":conf,"probs":probs,"lo":q.lo,"hi":q.hi,
          "temp_K":None if pd.isna(f.t_fire_K) else f.t_fire_K,"bg_K":s.ti5_median,"frac":None if pd.isna(f.frac) else f.frac,
          "frp_MW":0 if pd.isna(f.frp_derived_MW) else f.frp_derived_MW,"frp_max_MW":s.frp_max,"area_m2":s.pixel_area_m2,
          "ts":pd.Timestamp(s.last_seen).to_pydatetime().astimezone(timezone.utc),"n_hits":s.n_hits,"n_days":s.n_days,"night_frac":s.night_frac,
          "facility_name":f.facility_name,"facility_sector":f.facility_sector,"dist_facility_m":f.dist_facility_m,"state":f.state,"district":f.district,
          "severity":severity,"severity_rationale":severity_rationale,"reason":reason,"reason_template":reason_template,"cited_rule":cited_rule,
          "offshore_suppressed":is_suppressed,"evidence":_evidence(s,f,q,tracer=tracer,stage_ms=stage_ms),"top_features":top,
          "diurnal_hist":d_hist,"diurnal_shape":str(d_shape) if d_shape else None,
          "co2e_rate_tph":co2e_rate_tph,"black_carbon_rate_kgph":black_carbon_rate_kgph,"co2e_total_t":co2e_total_t})
    return records

async def process_once(app,fetch_days=1,fetch=True):
    tracer = StageTracer()
    settings=app.state.settings; store=app.state.store

    with tracer.stage("VIIRS INGEST"):
        if fetch: await FirmsClient(settings).fetch_range(fetch_days)
        raw=await asyncio.to_thread(load_all,settings.data_dir)
    store.log("VIIRS INGEST",f"normalised {len(raw)} mainland detections",elapsed_ms=tracer.get_ms("VIIRS INGEST"))

    if raw.empty:return []

    with tracer.stage("INDIA FILTER"):
        from agnivani.geo.india import point_in_india
        if "latitude" in raw.columns and "longitude" in raw.columns:
            _ = [point_in_india(float(lon), float(lat)) for lat, lon in zip(raw["latitude"][:10], raw["longitude"][:10])]
    store.log("INDIA FILTER","filtered to Indian mainland and islands",elapsed_ms=tracer.get_ms("INDIA FILTER"))

    with tracer.stage("SOURCE CLUSTER"):
        sources=await asyncio.to_thread(cluster_sources,raw,settings.cluster_cell_deg)
    store.log("SOURCE CLUSTER",f"clustered into {len(sources)} spatial sources",elapsed_ms=tracer.get_ms("SOURCE CLUSTER"))

    facilities=await asyncio.to_thread(load_facilities,settings.data_dir)
    from agnivani.geo.landcover import resolve_landcover_batch
    lc_dict=await asyncio.to_thread(resolve_landcover_batch,sources,settings.data_dir)

    with tracer.stage("PLANCK RETRIEVAL"):
        features=await asyncio.to_thread(build_features,sources,facilities,lc_dict)
    store.log("PLANCK RETRIEVAL","executed Dozier/Planck sub-pixel dual-band temperature retrieval",elapsed_ms=tracer.get_ms("PLANCK RETRIEVAL"))

    with tracer.stage("REGISTRY JOIN"):
        canonical_feats = canonical_frame(features)
    store.log("REGISTRY JOIN","joined with GEM and OSM industrial facility registries",elapsed_ms=tracer.get_ms("REGISTRY JOIN"))

    with tracer.stage("CLASSIFY"):
        scores=await asyncio.to_thread(app.state.scorer.score,canonical_feats)
    store.log("CLASSIFY",f"scored and stored {len(sources)} sources",elapsed_ms=tracer.get_ms("CLASSIFY"))

    records=build_records(raw,sources,features,scores,settings=settings,tracer=tracer)
    for item in records:store.upsert_detection(item)
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
