"""Auditable heuristic scorer and optional trained XGBoost scorer."""
from abc import ABC, abstractmethod
from pathlib import Path
import json, joblib
import numpy as np
import pandas as pd
from agnivani.features.build import FEATURES

CLASSES=["FLARE","IND_FIRE","COAL","WILD","LEAK"]

class BaseScorer(ABC):
    name="base"; version="0"
    @abstractmethod
    def score(self,X:pd.DataFrame)->pd.DataFrame: ...
    def metadata(self): return {"name":self.name,"version":self.version,"mode":self.name}

class HeuristicScorer(BaseScorer):
    name="heuristic"; version="1.0"
    def metadata(self): return {"name":self.name,"version":self.version,"mode":"heuristic","metrics":None,"disclosure":"Confidence values are hand-set expert priors, not trained probabilities."}
    def score(self,X):
        records=[]
        for _,r in X.iterrows():
            t=r.get("t_fire_K"); dist=r.get("dist_facility_m"); dist=dist if pd.notna(dist) else np.inf
            sector=r.get("facility_sector"); lc=r.get("landcover_class","unknown"); hour=np.arctan2(r.local_hour_sin,r.local_hour_cos)*24/(2*np.pi)%24
            if pd.isna(t) and dist<3000 and sector in {"REFI_GAS","FERTILIZER"} and r.night_frac>.5: cls,conf,why="LEAK",.55,"no MIR excess near gas-sector facility"
            elif pd.notna(t) and t>=1500 and r.night_frac>=.5 and r.n_days>=5 and r.frp_cv<.9 and dist<5000: cls,conf,why="FLARE",.90,"hot, persistent nighttime source near industrial facility"
            elif pd.notna(t) and t<1000 and r.span_days>=60 and np.expm1(r.log1p_frp_max)<5 and r.cluster_extent_m>1000: cls,conf,why="COAL",.82,"cool, spatially extended long-duration source"
            elif lc in {"forest","grassland","shrub"} and dist>5000 and r.span_days<30 and 10<=hour<=16: cls,conf,why="WILD",.78,"short-lived daytime vegetation fire away from facilities"
            elif r.n_days<=3 and np.expm1(r.log1p_frp_max)>20 and dist<3000: cls,conf,why="IND_FIRE",.84,"high-power short-duration event near facility"
            else: cls,conf,why="IND_FIRE",.35,"unresolved: low evidence"
            remainder=(1-conf)/(len(CLASSES)-1); probs={c:(conf if c==cls else remainder) for c in CLASSES}
            top=[("t_fire_K",float(t) if pd.notna(t) else 0.),("night_frac",float(r.night_frac)),("facility_distance",float(min(dist,1e6)))]
            records.append({"cls":cls,"conf":conf,"probs":probs,"lo":max(0,conf-.12),"hi":min(1,conf+.12),"reason":why,"top_features":top})
        return pd.DataFrame(records,index=X.index)

class XGBScorer(BaseScorer):
    name="xgboost"
    def __init__(self,data_dir):
        root=Path(data_dir)/"models"; paths=[root/"model.joblib",root/"calibrator.joblib",root/"conformal.json"]
        if not all(p.exists() for p in paths): raise FileNotFoundError("XGBoost artifacts missing: model.joblib, calibrator.joblib, or conformal.json")
        self.model,self.calibrator=joblib.load(paths[0]),joblib.load(paths[1]); self.conformal=json.loads(paths[2].read_text()); self.version=str(self.conformal.get("version","1"))
    def score(self,X):
        probs=self.calibrator.predict_proba(X[FEATURES].fillna(0)); labels=list(self.calibrator.classes_); q=float(self.conformal.get("q",.1)); out=[]
        for p in probs:
            i=int(np.argmax(p)); conf=float(p[i]); out.append({"cls":labels[i],"conf":conf,"probs":dict(zip(labels,map(float,p))),"lo":max(0,conf-q),"hi":min(1,conf+q),"reason":"trained model inference","top_features":[]})
        return pd.DataFrame(out,index=X.index)

def get_scorer(settings):
    if settings.scorer_backend=="xgboost":
        try:return XGBScorer(settings.data_dir)
        except FileNotFoundError:return HeuristicScorer()
    return HeuristicScorer()
