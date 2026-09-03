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
def detections(request:Request,bbox:str|None=None,hours:int=Query(24,ge=0),cls:list[str]|None=Query(None),min_conf:float=Query(0,ge=0,le=1),limit:int=Query(500,ge=1,le=5000)):
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
    for x in items:by_class[x["cls"]]+=1; by_severity[x["severity"]]+=1
    last=max((datetime.fromisoformat(x["ts"].replace("Z","+00:00")) for x in items),default=None)
    return {"total_detections":len(items),"total_sources":len(items),"by_class":by_class,"by_severity":by_severity,"last_ingest_utc":last,"scorer":request.app.state.scorer.metadata(),"coverage_pct":None}

@router.get("/facilities",response_model=list[FacilityOut])
def facilities(request:Request,sector:str|None=None):
    rows=request.app.state.store.query("SELECT payload FROM facilities"+(" WHERE sector=?" if sector else ""),[sector] if sector else [])
    return [json.loads(x) for x in rows.payload.tolist()]
