"""Tests for training set materialisation, spatial-block training, conformal calibration, and SHAP."""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import pytest

from agnivani.config import Settings
from agnivani.features.build import FEATURES
from agnivani.models.scorer import HeuristicScorer, XGBScorer, get_scorer
from agnivani.models.train import train
from scripts.materialise_training_set import materialise


def test_materialise_column_contract():
    df = materialise(data_dir=Path("data"), include_synthetic=False)
    required = set(FEATURES) | {"cls", "block_id"}
    assert required <= set(df.columns)
    assert len(df) > 0
    assert not df["cls"].isna().any()
    assert (df["cls"] != "UNLABELLED").all()


def test_train_writes_four_artifacts():
    data_dir = Path("data")
    train(data_dir=data_dir, dry_run=False)

    models_dir = data_dir / "models"
    assert (models_dir / "model.joblib").exists()
    assert (models_dir / "calibrator.joblib").exists()
    assert (models_dir / "conformal.json").exists()
    assert (models_dir / "metrics.json").exists()


def test_metrics_json_real_values():
    metrics_path = Path("data") / "models" / "metrics.json"
    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text())

    acc = metrics.get("spatial_block_cv_accuracy")
    assert acc is not None
    assert 0.0 <= acc <= 1.0

    macro_f1 = metrics.get("macro_f1")
    assert macro_f1 is not None
    assert 0.0 <= macro_f1 <= 1.0

    cov = metrics.get("conformal_coverage_pct")
    assert cov is not None
    assert 0.0 <= cov <= 100.0

    assert metrics.get("n_samples", 0) > 0
    assert metrics.get("n_blocks", 0) > 0
    assert "trained_at_utc" in metrics
    assert "label_provenance_counts" in metrics


def test_get_scorer_returns_xgboost_when_artifacts_exist():
    s = Settings(scorer_backend="xgboost", data_dir=Path("data"))
    scorer = get_scorer(s)
    assert isinstance(scorer, XGBScorer)
    assert scorer.name == "xgboost"
    meta = scorer.metadata()
    assert meta["mode"] == "xgboost"
    assert meta["metrics"] is not None
    assert "spatial_block_cv_accuracy" in meta["metrics"]


def test_get_scorer_falls_back_loudly_when_artifacts_missing(tmp_path):
    s = Settings(scorer_backend="xgboost", data_dir=tmp_path)
    scorer = get_scorer(s)
    assert isinstance(scorer, HeuristicScorer)
    assert scorer.mode == "fallback"
    meta = scorer.metadata()
    assert meta["mode"] == "fallback"
    assert "Fallback active" in meta["disclosure"]
    assert "missing" in meta["disclosure"]


def test_shap_contributions_are_real_floats():
    s = Settings(scorer_backend="xgboost", data_dir=Path("data"))
    scorer = get_scorer(s)
    assert isinstance(scorer, XGBScorer)
    df = pd.read_parquet("data/processed/labelled.parquet").head(2)
    scores = scorer.score(df)
    assert len(scores) == 2
    top = scores.iloc[0]["top_features"]
    assert len(top) > 0
    for item in top:
        assert "name" in item
        assert "value" in item
        assert "contribution" in item
        assert isinstance(item["contribution"], (float, int))
