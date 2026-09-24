"""Spatial-block training entry point. Requires externally labelled ground truth."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold
from xgboost import XGBClassifier

from agnivani.features.build import FEATURES, FORBIDDEN, spatial_block_id
from agnivani.models.evaluate import conformal_coverage
from agnivani.models.scorer import CLASSES


def train(data_dir: Path | str = Path("data"), dry_run: bool = False):
    leaks = set(FEATURES) & FORBIDDEN
    if leaks:
        raise RuntimeError(f"coordinate leakage candidates: {sorted(leaks)}")
    print("FEATURES:")
    for x in FEATURES:
        print(f"  {x}")

    path = Path(data_dir) / "processed" / "labelled.parquet"
    if not path.exists():
        raise FileNotFoundError("labelled.parquet is required; AGNIVANI never trains on heuristic-generated labels")
    df = pd.read_parquet(path)

    # Filter out UNLABELLED rows if present in the dataset so supervised training only trains on valid CLASSES
    if "label" in df.columns:
        if (df["label"] == "UNLABELLED").any():
            df = df[df["label"] != "UNLABELLED"].copy()

    # Normalization step BEFORE the missing-column check:
    # 1. Derive cls := label (map label->CLASSES; if a label is outside CLASSES raise with the offending value)
    if "label" in df.columns:
        offending = [x for x in df["label"].dropna().unique() if x not in CLASSES]
        if offending:
            raise ValueError(f"Offending label(s) outside CLASSES found: {sorted(offending)}. Valid CLASSES: {CLASSES}")
        df["cls"] = df["label"]
    elif "cls" in df.columns:
        offending = [x for x in df["cls"].dropna().unique() if x not in CLASSES]
        if offending:
            raise ValueError(f"Offending cls value(s) outside CLASSES: {sorted(offending)}. Valid CLASSES: {CLASSES}")
    else:
        raise ValueError("Neither 'label' nor 'cls' column found in labelled.parquet")

    # 2. Derive block_id := spatial_block_id(centroid_lat, centroid_lon)
    if "block_id" not in df.columns:
        if "centroid_lat" in df.columns and "centroid_lon" in df.columns:
            df["block_id"] = [
                spatial_block_id(float(lat), float(lon))
                for lat, lon in zip(df["centroid_lat"], df["centroid_lon"])
            ]
        else:
            raise ValueError("Cannot derive block_id: missing 'centroid_lat' or 'centroid_lon'")

    # 3. Re-index on source_id
    if "source_id" in df.columns:
        df = df.set_index("source_id", drop=False)

    # 4. Assert set(FEATURES) is a subset; if still missing, FAIL LOUD (raise)
    missing_features = set(FEATURES) - set(df.columns)
    if missing_features:
        raise ValueError(f"labelled data missing required FEATURES: {sorted(missing_features)}")

    required = set(FEATURES) | {"cls", "block_id"}
    if missing := required - set(df.columns):
        raise ValueError(f"labelled data missing: {sorted(missing)}")

    if dry_run:
        print(f"[ok] dry-run passed: required set {len(required)} columns verified on {len(df)} rows")
        return

    import sklearn.base
    try:
        sklearn.base.ClassifierMixin.__sklearn_tags__ = lambda self: sklearn.base.BaseEstimator.__sklearn_tags__(self)
    except Exception:
        pass

    unique_classes = sorted(df["cls"].unique())
    class_to_idx = {c: i for i, c in enumerate(unique_classes)}
    y = df["cls"].map(class_to_idx).astype(int)
    weights = np.where(df["origin"] == "real", 2.0, 1.0) if "origin" in df.columns else None

    X = df[FEATURES].copy()
    if "diurnal_shape" in X.columns:
        from agnivani.features.build import DIURNAL_SHAPES
        shape_to_idx = {s: float(i) for i, s in enumerate(DIURNAL_SHAPES)}
        X["diurnal_shape"] = X["diurnal_shape"].map(lambda v: shape_to_idx.get(v, float(v) if isinstance(v, (int, float)) else 4.0))
    X = X.astype(float).fillna(0.0)

    # Spatial-block cross-validation
    n_splits = min(5, df["block_id"].nunique())
    cv = GroupKFold(n_splits=n_splits)

    oof_preds = np.zeros(len(y), dtype=int)
    oof_probs = np.zeros((len(y), len(unique_classes)))

    for tr, te in cv.split(X, y, df["block_id"]):
        fold_model = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42)
        w_tr = weights[tr] if weights is not None else None
        fold_model.fit(X.iloc[tr], y.iloc[tr], sample_weight=w_tr)
        oof_preds[te] = fold_model.predict(X.iloc[te])
        oof_probs[te] = fold_model.predict_proba(X.iloc[te])

    spatial_block_cv_accuracy = float(accuracy_score(y, oof_preds))
    macro_f1 = float(f1_score(y, oof_preds, average="macro"))
    per_class_f1_arr = f1_score(y, oof_preds, average=None)
    per_class_f1 = {cls_name: float(round(score, 4)) for cls_name, score in zip(unique_classes, per_class_f1_arr)}

    # Conformal calibration on out-of-fold spatial predictions
    p_true = [float(oof_probs[i, y.iloc[i]]) for i in range(len(y))]
    non_conf = [1.0 - pt for pt in p_true]
    q = float(round(float(np.quantile(non_conf, 0.90)), 4))
    lo = np.maximum(0.0, oof_probs.max(axis=1) - q)
    hi = np.minimum(1.0, oof_probs.max(axis=1) + q)
    cov_frac = conformal_coverage(oof_probs.max(axis=1), lo, hi)
    conformal_coverage_pct = float(round(cov_frac * 100.0, 2))

    # Fit final production model and calibrator on all data
    model = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42)
    model.fit(X, y, sample_weight=weights)

    out = Path(data_dir) / "models"
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out / "model.joblib")

    calibrator = CalibratedClassifierCV(estimator=model, cv="prefit")
    calibrator.fit(X, y)
    joblib.dump(calibrator, out / "calibrator.joblib")

    conformal_data = {
        "version": "1.0",
        "q": q,
        "coverage_level": 0.90,
        "classes": unique_classes,
    }
    (out / "conformal.json").write_text(json.dumps(conformal_data, indent=2))

    provenance_counts = (
        df["origin"].value_counts().to_dict()
        if "origin" in df.columns
        else {"real": int(len(df))}
    )
    metrics_data = {
        "spatial_block_cv_accuracy": float(round(spatial_block_cv_accuracy, 4)),
        "macro_f1": float(round(macro_f1, 4)),
        "per_class_f1": per_class_f1,
        "conformal_coverage_pct": conformal_coverage_pct,
        "n_samples": int(len(df)),
        "n_blocks": int(df["block_id"].nunique()),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "label_provenance_counts": provenance_counts,
    }
    (out / "metrics.json").write_text(json.dumps(metrics_data, indent=2))

    print(f"[ok] model and calibrated artifacts saved to {out}")
    print(f"[ok] metrics: accuracy={spatial_block_cv_accuracy:.4f}, macro_f1={macro_f1:.4f}, coverage={conformal_coverage_pct}%")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    a = p.parse_args()
    train(a.data_dir, a.dry_run)
