import pytest
import numpy as np
import pandas as pd
from agnivani.features.build import FEATURES, canonical_frame
from agnivani.models.scorer import HeuristicScorer, CLASSES

def test_classes_count_and_probabilities_sum():
    assert len(CLASSES) == 6
    assert "UNRESOLVED" in CLASSES

    scorer = HeuristicScorer()
    dummy_input = pd.DataFrame([{
        "dist_facility_m": 1000.0,
        "facility_sector": "STEEL",
        "landcover_class": "built",
        "t_fire_K": 1600.0,
        "night_frac": 0.8,
        "n_days": 10,
        "frp_cv": 0.5,
        "local_hour_sin": 0.0,
        "local_hour_cos": 1.0,
        "log1p_frp_max": 2.0,
    }])
    scores = scorer.score(dummy_input)
    assert len(scores) == 1
    p = scores.iloc[0]["probs"]
    assert len(p) == 6
    assert abs(sum(p.values()) - 1.0) < 1e-9

def test_bare_features_raises_value_error():
    scorer = HeuristicScorer()
    bare_df = pd.DataFrame([{f: 0.0 for f in FEATURES}])
    with pytest.raises(ValueError, match="HeuristicScorer requires context columns"):
        scorer.score(bare_df)

def test_av_8a95cffe_unresolved():
    scorer = HeuristicScorer()
    av_row = pd.DataFrame([{
        "source_id": "AV-8A95CFFE",
        "dist_facility_m": 80720.048,
        "facility_name": None,
        "facility_sector": None,
        "landcover_class": "unknown",
        "n_days": 1,
        "frp_max": 8.3,
        "log1p_frp_max": np.log1p(8.3),
        "night_frac": 0.0,
        "local_hour_sin": np.sin(2 * np.pi * 13 / 24),
        "local_hour_cos": np.cos(2 * np.pi * 13 / 24),
        "t_fire_K": np.nan,
        "span_days": 1,
        "frp_cv": 0.0,
        "cluster_extent_m": 0.0,
    }])
    scored = scorer.score(av_row)
    assert len(scored) == 1
    row_out = scored.iloc[0]
    assert row_out["cls"] == "UNRESOLVED"
    assert row_out["cls"] != "IND_FIRE"
    assert abs(sum(row_out["probs"].values()) - 1.0) < 1e-9
