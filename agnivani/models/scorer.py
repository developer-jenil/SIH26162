"""Auditable heuristic scorer and optional trained XGBoost scorer."""
from abc import ABC, abstractmethod
from pathlib import Path
import json, joblib
import numpy as np
import pandas as pd
from agnivani.features.build import FEATURES

try:
    import sklearn.base
    sklearn.base.ClassifierMixin.__sklearn_tags__ = lambda self: sklearn.base.BaseEstimator.__sklearn_tags__(self)
except Exception:
    pass

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
            fac_name=r.get("facility_name"); lc_water=r.get("landcover_water", 0.0); frp_max=np.expm1(r.get("log1p_frp_max", 0.0))
            is_offshore = bool((lc_water == 1.0) or ((pd.isna(fac_name) or fac_name is None) and dist > 25000 and frp_max < 5))

            shape=r.get("diurnal_shape") or "SPARSE"
            is_cropland=bool(lc=="cropland" or r.get("landcover_cropland", 0.0)==1.0)

            if is_offshore:
                cls,conf,why="IND_FIRE",.10,"unverified/offshore-suppressed"
            elif pd.isna(t) and dist<3000 and sector in {"REFI_GAS","FERTILIZER"} and r.night_frac>.5: cls,conf,why="LEAK",.55,"no MIR excess near gas-sector facility"
            elif pd.notna(t) and t>=1500 and r.night_frac>=.5 and r.n_days>=5 and r.frp_cv<.9 and dist<5000: cls,conf,why="FLARE",.90,"hot, persistent nighttime source near industrial facility"
            elif pd.notna(t) and t<1000 and r.span_days>=60 and np.expm1(r.log1p_frp_max)<5 and r.cluster_extent_m>1000: cls,conf,why="COAL",.82,"cool, spatially extended long-duration source"
            elif is_cropland and (shape=="EVENING_BURST" or (16<=hour<=20 and dist>2000)): cls,conf,why="WILD",.85,"agricultural stubble burning (cropland evening burst)"
            elif lc in {"forest","grassland","shrub"} and dist>5000 and r.span_days<30 and 10<=hour<=16: cls,conf,why="WILD",.78,"short-lived daytime vegetation fire away from facilities"
            elif shape=="FLAT_24H" and dist<5000 and r.night_frac>=.35: cls,conf,why="FLARE",.88,"persistent 24h flat profile near industrial facility"
            elif shape=="DAYTIME_ONLY" and dist>5000: cls,conf,why="WILD",.80,"daytime-only vegetation fire pattern away from facilities"
            elif r.n_days<=3 and np.expm1(r.log1p_frp_max)>20 and dist<3000: cls,conf,why="IND_FIRE",.84,"high-power short-duration event near facility"
            else: cls,conf,why="IND_FIRE",.35,"unresolved: low evidence"

            remainder=(1-conf)/(len(CLASSES)-1); probs={c:(conf if c==cls else remainder) for c in CLASSES}
            top=[("t_fire_K",float(t) if pd.notna(t) else 0.),("night_frac",float(r.night_frac)),("facility_distance",float(min(dist,1e6)))]
            records.append({"cls":cls,"conf":conf,"probs":probs,"lo":max(0,conf-.12),"hi":min(1,conf+.12),"reason":why,"top_features":top,"offshore_suppressed":is_offshore})
        return pd.DataFrame(records,index=X.index)

class XGBScorer(BaseScorer):
    name="xgboost"
    def __init__(self,data_dir):
        root=Path(data_dir)/"models"; paths=[root/"model.joblib",root/"calibrator.joblib",root/"conformal.json"]
        missing = [p.name for p in paths if not p.exists()]
        if missing:
            raise FileNotFoundError(f"XGBoost model artifacts missing ({missing}) in '{root}'. Train the model first using: python -m agnivani.models.train")
        self.model,self.calibrator=joblib.load(paths[0]),joblib.load(paths[1]); self.conformal=json.loads(paths[2].read_text()); self.version=str(self.conformal.get("version","1"))
    def score(self,X):
        from agnivani.features.build import DIURNAL_SHAPES
        X_feat = X[FEATURES].copy()
        if "diurnal_shape" in X_feat.columns:
            shape_to_idx = {s: float(i) for i, s in enumerate(DIURNAL_SHAPES)}
            X_feat["diurnal_shape"] = X_feat["diurnal_shape"].map(lambda v: shape_to_idx.get(v, float(v) if isinstance(v, (int, float)) else 4.0))
        probs=self.calibrator.predict_proba(X_feat.astype(float).fillna(0.0)); labels=self.conformal.get("classes", CLASSES); q=float(self.conformal.get("q",.1)); out=[]
        for i,p in enumerate(probs):
            idx=int(np.argmax(p)); conf=float(p[idx]); cls=labels[idx]
            r=X.iloc[i]; fac_name=r.get("facility_name"); dist=r.get("dist_facility_m"); dist=dist if pd.notna(dist) else np.inf
            lc_water=r.get("landcover_water", 0.0); frp_max=np.expm1(r.get("log1p_frp_max", 0.0))
            is_offshore = bool((lc_water == 1.0) or ((pd.isna(fac_name) or fac_name is None) and dist > 25000 and frp_max < 5))
            if is_offshore:
                conf = min(conf, 0.10)
                reason = "unverified/offshore-suppressed"
                remainder = (1 - conf) / (len(labels) - 1)
                p_dict = {c: (conf if c == cls else remainder) for c in labels}
            else:
                reason = "trained model inference"
                p_dict = dict(zip(labels, map(float, p)))
            out.append({"cls":cls,"conf":conf,"probs":p_dict,"lo":max(0,conf-q),"hi":min(1,conf+q),"reason":reason,"top_features":[],"offshore_suppressed":is_offshore})
        return pd.DataFrame(out,index=X.index)

def get_scorer(settings):
    if settings.scorer_backend=="xgboost":
        return XGBScorer(settings.data_dir)
    return HeuristicScorer()
