"""Tests for synthetic blob generation, physics grounding, and model dataset integration."""
from pathlib import Path
import pandas as pd
import pytest

from agnivani.geo.registry import generate_synthetic_blobs, load_facilities
from agnivani.models.scorer import HeuristicScorer, CLASSES
from agnivani.models.train import train
from agnivani.features.build import FEATURES


def test_synthetic_flare_satisfies_flare_rule(tmp_path):
    facs = load_facilities(tmp_path)
    synth = generate_synthetic_blobs(facs, n_per_sector=10, seed=42)
    flares = synth[synth["label"] == "FLARE"]
    assert len(flares) == 10

    scorer = HeuristicScorer()
    scored = scorer.score(flares)

    assert (scored["cls"] == "FLARE").all(), f"Not all synthetic FLARE rows classified as FLARE: {scored['cls'].tolist()}"
    assert (scored["conf"] == 0.90).all()
    assert (scored["reason"] == "hot, persistent nighttime source near industrial facility").all()
    assert not scored["offshore_suppressed"].any()


def test_synthetic_wild_has_landcover_forest(tmp_path):
    facs = load_facilities(tmp_path)
    synth = generate_synthetic_blobs(facs, n_per_sector=10, seed=42)
    wilds = synth[synth["label"] == "WILD"]
    assert len(wilds) == 10

    assert (wilds["landcover_forest"] == 1.0).all(), "All synthetic WILD rows must have landcover_forest=1.0"
    assert (wilds["landcover_cropland"] == 0.0).all()
    assert (wilds["landcover_water"] == 0.0).all()
    assert (wilds["landcover_built"] == 0.0).all()

    scorer = HeuristicScorer()
    scored = scorer.score(wilds)
    assert (scored["cls"] == "WILD").all()
    assert (scored["conf"] == 0.78).all()


def test_labelled_parquet_passes_train_dry_run(tmp_path):
    facs = load_facilities(tmp_path)
    # Generate synthetic blobs into tmp_path
    synth = generate_synthetic_blobs(facs, n_per_sector=5, seed=42, data_dir=tmp_path)
    lab_path = tmp_path / "processed" / "labelled.parquet"
    assert lab_path.exists()

    df = pd.read_parquet(lab_path)
    assert set(FEATURES).issubset(set(df.columns))
    assert "origin" in df.columns
    assert (df["origin"] == "synthetic").any()

    # Dry-run must pass without error and assert required-set check
    train(data_dir=tmp_path, dry_run=True)
