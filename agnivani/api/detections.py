"""Detection, statistics, health, and facility endpoints."""
from datetime import datetime, timezone
import json
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from .schemas import DetectionOut, FacilityOut, StatsOut
from agnivani.models.scorer import CLASSES
router=APIRouter()

def _parse_bbox(value):
    if not value:return None
    try:
        numbers=[float(x) for x in value.split(",")]
        if len(numbers)!=4:raise ValueError
        return numbers
    except ValueError:raise HTTPException(422,"bbox must be minx,miny,maxx,maxy")

@router.get("/health")
def health(request:Request):
    latest=request.app.state.store.query("SELECT max(ts) latest FROM detections").iloc[0,0]
    age=int((datetime.now(timezone.utc)-latest.to_pydatetime()).total_seconds()) if latest is not None and not pd.isna(latest) else -1
    return {"ok":True,"scorer":request.app.state.scorer.metadata(),"ingest_age_s":age}

@router.get("/detections",response_model=list[DetectionOut])
def detections(request:Request,bbox:str|None=None,hours:int=Query(0,ge=0),cls:list[str]|None=Query(None),min_conf:float=Query(0,ge=0,le=1),limit:int=Query(500,ge=1,le=5000)):
    items=request.app.state.store.detections(); bounds=_parse_bbox(bbox); now=datetime.now(timezone.utc)
    filtered=[]
    for x in items:
        ts=datetime.fromisoformat(x["ts"].replace("Z","+00:00"))
        if hours and (now-ts).total_seconds()>hours*3600:continue
        if cls and x["cls"] not in cls:continue
        if x["conf"]<min_conf:continue
        if bounds and not(bounds[0]<=x["lon"]<=bounds[2] and bounds[1]<=x["lat"]<=bounds[3]):continue
        filtered.append(x)
    return filtered[:limit]

@router.get("/detections/{detection_id}",response_model=DetectionOut)
def detection(request:Request,detection_id:str):
    df=request.app.state.store.query("SELECT payload FROM detections WHERE id=?",[detection_id])
    if df.empty:raise HTTPException(404,f"Detection '{detection_id}' was not found")
    return json.loads(df.iloc[0,0])

@router.get("/stats",response_model=StatsOut)
def stats(request:Request):
    items=request.app.state.store.detections(); by_class={x:0 for x in CLASSES}; by_severity={x:0 for x in ["CRITICAL","HIGH","MODERATE","LOW"]}
    for x in items:
        if x["cls"] in by_class:
            by_class[x["cls"]]+=1
        by_severity[x["severity"]]+=1
    last=max((datetime.fromisoformat(x["ts"].replace("Z","+00:00")) for x in items),default=None)
    scorer_meta = request.app.state.scorer.metadata()
    cov_pct = None
    if scorer_meta and scorer_meta.get("metrics"):
        cov_pct = scorer_meta["metrics"].get("conformal_coverage_pct")
    return {"total_detections":len(items),"total_sources":len(items),"by_class":by_class,"by_severity":by_severity,"last_ingest_utc":last,"scorer":scorer_meta,"coverage_pct":cov_pct}

@router.get("/facilities",response_model=list[FacilityOut])
def facilities(request:Request,sector:str|None=None):
    rows=request.app.state.store.query("SELECT payload FROM facilities"+(" WHERE sector=?" if sector else ""),[sector] if sector else [])
    return [json.loads(x) for x in rows.payload.tolist()]

@router.get("/facilities/{facility_id}/matches",response_model=list[DetectionOut])
@router.get("/facilities/{facility_id}/detections",response_model=list[DetectionOut])
def facility_matches(request:Request,facility_id:str):
    """Return all detections matched to facility_id using registry.nearest_facility and match_radius_m."""
    store=request.app.state.store
    rows=store.query("SELECT payload FROM facilities")
    all_facs=[json.loads(x) for x in rows.payload.tolist()]
    target_fac=None
    for f in all_facs:
        if f.get("facility_id")==facility_id or f.get("name","").lower()==facility_id.lower():
            target_fac=f
            break
    if target_fac is None:
        raise HTTPException(404,f"Facility '{facility_id}' was not found")

    from agnivani.geo.registry import load_facilities, nearest_facility
    facilities_gdf=load_facilities(request.app.state.settings.data_dir)
    target_row=facilities_gdf[facilities_gdf["facility_id"]==target_fac["facility_id"]]
    match_radius_m=float(target_fac.get("match_radius_m") or (target_row.iloc[0].get("match_radius_m") if not target_row.empty else 2000.0) or 2000.0)

    items=store.detections()
    matched=[]
    for d in items:
        fac_obj,dist_m=nearest_facility(facilities_gdf,d["lat"],d["lon"],max_dist_m=match_radius_m)
        if fac_obj and fac_obj.facility_id==target_fac["facility_id"]:
            matched.append(d)
        elif d.get("facility_name")==target_fac["name"] and (d.get("dist_facility_m") is None or d.get("dist_facility_m")<=match_radius_m):
            matched.append(d)
    return matched
