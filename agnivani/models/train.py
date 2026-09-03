"""Spatial-block training entry point. Requires externally labelled ground truth."""
import argparse
from pathlib import Path
import joblib, pandas as pd
from sklearn.model_selection import GroupKFold
from xgboost import XGBClassifier
from agnivani.features.build import FEATURES, FORBIDDEN


def train(data_dir=Path("data"), dry_run=False):
    leaks=set(FEATURES)&FORBIDDEN
    if leaks: raise RuntimeError(f"coordinate leakage candidates: {sorted(leaks)}")
    print("FEATURES:"); [print(f"  {x}") for x in FEATURES]
    if dry_run:return
    path=Path(data_dir)/"processed"/"labelled.parquet"
    if not path.exists(): raise FileNotFoundError("labelled.parquet is required; AGNIVANI never trains on heuristic-generated labels")
    df=pd.read_parquet(path); required=set(FEATURES)|{"cls","block_id"}
    if missing:=required-set(df): raise ValueError(f"labelled data missing: {sorted(missing)}")
    cv=GroupKFold(n_splits=min(5,df.block_id.nunique()))
    model=XGBClassifier(n_estimators=300,max_depth=6,learning_rate=.05)
    for train_idx,test_idx in cv.split(df[FEATURES],df.cls,df.block_id): model.fit(df.iloc[train_idx][FEATURES],df.iloc[train_idx].cls)
    model.fit(df[FEATURES],df.cls); out=Path(data_dir)/"models"; out.mkdir(parents=True,exist_ok=True); joblib.dump(model,out/"model.joblib")

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--dry-run",action="store_true"); p.add_argument("--data-dir",type=Path,default=Path("data")); a=p.parse_args(); train(a.data_dir,a.dry_run)
