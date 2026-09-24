"""Inference backends: deterministic HeuristicScorer and ML-based XGBScorer."""
from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import structlog

from agnivani.features.build import FEATURES

log = structlog.get_logger(__name__)

try:
    import sklearn.base
    from sklearn.utils._tags import Tags, TargetTags, ClassifierTags
    sklearn.base.ClassifierMixin.__sklearn_tags__ = lambda self: Tags(
        estimator_type="classifier",
        target_tags=TargetTags(required=True),
        classifier_tags=ClassifierTags(),
    )
except Exception:
    pass

CLASSES = ["FLARE", "IND_FIRE", "COAL", "WILD", "LEAK", "UNRESOLVED"]



class BaseScorer(ABC):
    name = "base"
    version = "0"

    @abstractmethod
    def score(self, X: pd.DataFrame) -> pd.DataFrame: ...

    def metadata(self):
        return {"name": self.name, "version": self.version, "mode": self.name}


class HeuristicScorer(BaseScorer):
    name = "heuristic"
    version = "1.0"
    mode = "heuristic"
    fallback_disclosure: str | None = None
    metrics: dict | None = None

    def metadata(self):
        disc = (
            self.fallback_disclosure
            if self.mode == "fallback"
            else "Confidence values are hand-set expert priors, not trained probabilities."
        )
        return {
            "name": self.name,
            "version": self.version,
            "mode": self.mode,
            "metrics": self.metrics,
            "disclosure": disc,
        }

    def score(self, X: pd.DataFrame) -> pd.DataFrame:
        required_context = ["dist_facility_m", "facility_sector", "landcover_class"]
        missing = [c for c in required_context if c not in X.columns]
        if missing:
            raise ValueError(
                f"HeuristicScorer requires context columns {missing}. "
                "Slicing to FEATURES alone silently breaks context rules. Use canonical_frame()."
            )
        records = []
        for _, r in X.iterrows():
            t = r.get("t_fire_K")
            dist = r.get("dist_facility_m")
            dist = dist if pd.notna(dist) else np.inf
            sector = r.get("facility_sector")
            lc = r.get("landcover_class", "unknown")
            hour = np.arctan2(r.local_hour_sin, r.local_hour_cos) * 24 / (2 * np.pi) % 24
            fac_name = r.get("facility_name")
            lc_water = r.get("landcover_water", 0.0)
            frp_max = np.expm1(r.get("log1p_frp_max", 0.0))
            is_offshore = bool((lc_water == 1.0) or ((pd.isna(fac_name) or fac_name is None) and dist > 25000 and frp_max < 5))

            shape = r.get("diurnal_shape") or "SPARSE"
            is_cropland = bool(lc == "cropland" or r.get("landcover_cropland", 0.0) == 1.0)

            if is_offshore:
                cls, conf, why = "UNRESOLVED", 0.10, "unverified/offshore-suppressed"
            elif pd.isna(t) and dist < 3000 and sector in {"REFI_GAS", "FERTILIZER"} and r.night_frac > 0.5:
                cls, conf, why = "LEAK", 0.55, "no MIR excess near gas-sector facility"
            elif pd.notna(t) and t >= 1500 and r.night_frac >= 0.5 and r.n_days >= 5 and r.frp_cv < 0.9 and dist < 5000:
                cls, conf, why = "FLARE", 0.90, "hot, persistent nighttime source near industrial facility"
            elif pd.notna(t) and t < 1000 and r.span_days >= 60 and np.expm1(r.log1p_frp_max) < 5 and r.cluster_extent_m > 1000:
                cls, conf, why = "COAL", 0.82, "cool, spatially extended long-duration source"
            elif is_cropland and (shape == "EVENING_BURST" or (16 <= hour <= 20 and dist > 2000)):
                cls, conf, why = "WILD", 0.85, "agricultural stubble burning (cropland evening burst)"
            elif lc in {"forest", "grassland", "shrub"} and dist > 5000 and r.span_days < 30 and 10 <= hour <= 16:
                cls, conf, why = "WILD", 0.78, "short-lived daytime vegetation fire away from facilities"
            elif shape == "FLAT_24H" and dist < 5000 and r.night_frac >= 0.35:
                cls, conf, why = "FLARE", 0.88, "persistent 24h flat profile near industrial facility"
            elif shape == "DAYTIME_ONLY" and dist > 5000:
                cls, conf, why = "WILD", 0.80, "daytime-only vegetation fire pattern away from facilities"
            elif r.n_days <= 3 and np.expm1(r.log1p_frp_max) > 20 and dist < 3000:
                cls, conf, why = "IND_FIRE", 0.84, "high-power short-duration event near facility"
            else:
                cls, conf, why = "UNRESOLVED", 0.35, "insufficient evidence for confident attribution"

            remainder = (1 - conf) / (len(CLASSES) - 1)
            probs = {c: (conf if c == cls else remainder) for c in CLASSES}
            top = [
                {"name": "t_fire_K", "value": float(t) if pd.notna(t) else 0.0, "contribution": None},
                {"name": "night_frac", "value": float(r.night_frac), "contribution": None},
                {"name": "facility_distance", "value": float(min(dist, 1e6)), "contribution": None},
            ]
            records.append({
                "cls": cls,
                "conf": conf,
                "probs": probs,
                "lo": max(0.0, conf - 0.12),
                "hi": min(1.0, conf + 0.12),
                "reason": why,
                "top_features": top,
                "offshore_suppressed": is_offshore,
            })
        return pd.DataFrame(records, index=X.index)


class XGBScorer(BaseScorer):
    name = "xgboost"
    mode = "xgboost"

    def __init__(self, data_dir: Path | str = Path("data")):
        root = Path(data_dir) / "models"
        paths = [root / "model.joblib", root / "calibrator.joblib", root / "conformal.json"]
        missing = [p.name for p in paths if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"XGBoost model artifacts missing ({missing}) in '{root}'. "
                "Train the model first using: python -m agnivani.models.train"
            )
        self.data_dir = Path(data_dir)
        self.model = joblib.load(paths[0])
        self.calibrator = joblib.load(paths[1])
        self.conformal = json.loads(paths[2].read_text())
        self.version = str(self.conformal.get("version", "1.0"))
        metrics_p = root / "metrics.json"
        self.metrics = json.loads(metrics_p.read_text()) if metrics_p.exists() else None
        self._explainer = None

    def metadata(self):
        return {
            "name": self.name,
            "version": self.version,
            "mode": self.mode,
            "metrics": self.metrics,
            "disclosure": "Trained XGBoost classifier with spatial-block cross-validation and conformal prediction.",
        }

    def score(self, X: pd.DataFrame) -> pd.DataFrame:
        from agnivani.features.build import DIURNAL_SHAPES

        X_feat = X[FEATURES].copy()
        if "diurnal_shape" in X_feat.columns:
            shape_to_idx = {s: float(i) for i, s in enumerate(DIURNAL_SHAPES)}
            X_feat["diurnal_shape"] = X_feat["diurnal_shape"].map(
                lambda v: shape_to_idx.get(v, float(v) if isinstance(v, (int, float)) else 4.0)
            )
        X_mat = X_feat.astype(float).fillna(0.0)
        probs = self.calibrator.predict_proba(X_mat)
        labels = self.conformal.get("classes", CLASSES)
        q = float(self.conformal.get("q", 0.1))

        # Vectorized SHAP computation via TreeExplainer
        shap_top_features = []
        try:
            if self._explainer is None:
                import shap

                self._explainer = shap.TreeExplainer(self.model)
            shap_vals = self._explainer.shap_values(X_mat)
            for i, p in enumerate(probs):
                class_idx = int(np.argmax(p))
                if isinstance(shap_vals, list):
                    sample_shap = shap_vals[class_idx][i]
                elif shap_vals.ndim == 3:
                    # Guard for class_idx in bounds
                    c_idx = class_idx if class_idx < shap_vals.shape[2] else 0
                    sample_shap = shap_vals[i, :, c_idx]
                else:
                    sample_shap = shap_vals[i]

                top_idx = np.argsort(np.abs(sample_shap))[::-1][:3]
                top_items = [
                    {
                        "name": FEATURES[idx],
                        "value": float(X_mat.iloc[i, idx]),
                        "contribution": float(round(float(sample_shap[idx]), 4)),
                    }
                    for idx in top_idx
                ]
                shap_top_features.append(top_items)
        except Exception as exc:
            log.warning("shap_computation_failed", error=str(exc))
            shap_top_features = [[] for _ in range(len(X))]

        out = []
        for i, p in enumerate(probs):
            idx = int(np.argmax(p))
            conf = float(p[idx])
            cls = labels[idx] if idx < len(labels) else "UNRESOLVED"
            r = X.iloc[i]
            fac_name = r.get("facility_name")
            dist = r.get("dist_facility_m")
            dist = dist if pd.notna(dist) else np.inf
            lc_water = r.get("landcover_water", 0.0)
            frp_max = np.expm1(r.get("log1p_frp_max", 0.0))
            is_offshore = bool((lc_water == 1.0) or ((pd.isna(fac_name) or fac_name is None) and dist > 25000 and frp_max < 5))

            if is_offshore:
                cls = "UNRESOLVED"
                conf = min(conf, 0.10)
                reason = "unverified/offshore-suppressed"
                remainder = (1 - conf) / (len(labels) - 1) if len(labels) > 1 else 0.0
                p_dict = {c: (conf if c == cls else remainder) for c in labels}
            else:
                reason = "trained model inference"
                p_dict = {c: float(prob) for c, prob in zip(labels, p)}

            out.append({
                "cls": cls,
                "conf": conf,
                "probs": p_dict,
                "lo": max(0.0, conf - q),
                "hi": min(1.0, conf + q),
                "reason": reason,
                "top_features": shap_top_features[i] if i < len(shap_top_features) else [],
                "offshore_suppressed": is_offshore,
            })
        return pd.DataFrame(out, index=X.index)


def get_scorer(settings) -> BaseScorer:
    """Return configured scorer backend. On missing XGBoost artifacts, log at ERROR and fall back with disclosure."""
    if settings.scorer_backend == "xgboost":
        try:
            return XGBScorer(settings.data_dir)
        except FileNotFoundError as exc:
            log.error("xgboost_artifacts_missing_fallback", error=str(exc))
            scorer = HeuristicScorer()
            scorer.mode = "fallback"
            scorer.fallback_disclosure = f"Fallback active: {str(exc)}"
            return scorer
    return HeuristicScorer()
