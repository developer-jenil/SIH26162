"""Pydantic wire contract consumed by the dashboard and OpenAPI clients."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

ClassName=Literal["FLARE","IND_FIRE","COAL","WILD","LEAK","UNRESOLVED","GEO","UNAUTHORISED"]

class EvidenceStage(BaseModel):
    stage:int=Field(ge=1,le=6); label:str; status:Literal["ok","warn","fail"]; detail:str; value:str|None=None; ms:int=Field(ge=0)
class FeatureContrib(BaseModel): name:str; value:float; contribution:float|None=None
class DetectionOut(BaseModel):
    id:str; lat:float; lon:float; cls:ClassName; conf:float=Field(ge=0,le=1); probs:dict[str,float]; lo:float; hi:float
    temp_K:float|None; bg_K:float; frac:float|None; frp_MW:float; frp_max_MW:float; area_m2:float; ts:datetime
    n_hits:int; n_days:int; night_frac:float; facility_name:str|None=None; facility_sector:str|None=None
    dist_facility_m:float|None=None; state:str|None=None; district:str|None=None
    severity:Literal["CRITICAL","HIGH","MODERATE","LOW"]; severity_rationale:str|None=None; reason:str; reason_template:str|None=None; cited_rule:str|None=None; offshore_suppressed:bool=False; evidence:list[EvidenceStage]; top_features:list[FeatureContrib]
    diurnal_hist:list[float]|None=None; diurnal_shape:str|None=None
    co2e_rate_tph:float|None=None; black_carbon_rate_kgph:float|None=None; co2e_total_t:float|None=None
    landcover_class:str|None=None; landcover_status:str|None=None
class StatsOut(BaseModel):
    total_detections:int; total_sources:int; by_class:dict[str,int]; by_severity:dict[str,int]; last_ingest_utc:datetime|None; scorer:dict; coverage_pct:float|None=None
class DispatchRequest(BaseModel): detection_id:str; authority:str; channel:Literal["sms","email","api","mock"]; note:str|None=None
class DispatchOut(BaseModel): dispatch_id:str; status:Literal["queued","sent","failed"]; receipt:str|None=None; dispatched_at:datetime
class FacilityOut(BaseModel): facility_id:str; name:str; lat:float; lon:float; sector:str; district:str|None=None; state:str|None=None; source_of_truth:str
class PipelineLogOut(BaseModel): id:int; ts:datetime; stage:str; level:str; message:str; elapsed_ms:int|None=None
