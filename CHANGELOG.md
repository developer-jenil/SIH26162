# Changelog

All notable changes to the AGNIVANI project will be documented in this file.

## [Phase 0] - Integrity Hardening (2026-09-24)

### Fixed
- **D1 (Severity from physics, not confidence)**: Created `agnivani/models/severity.py` with `compute_severity(cls, frp_mw, deviation_z, population_in_radius, offshore_suppressed)`. Replaced hardcoded confidence-based severity in `scheduler.py`. Routine flares with low FRP now map to `LOW`, high-FRP industrial fires escalate to `CRITICAL`, and gas leaks default to `HIGH`/`CRITICAL`.
- **D3, D4 (Unresolved fallback & canonical scoring frame)**: Added `"UNRESOLVED"` class to `CLASSES`. Slicing to `FEATURES` alone previously stripped context columns required by `HeuristicScorer`; added `canonical_frame()` in `agnivani/features/build.py` and routed all scoring through it with explicit missing-column guards in `HeuristicScorer.score()`. Distant detections (`dist > 25 km`) without physical flareup proof are prevented from being labelled `IND_FIRE`.
- **D8 (Real pipeline telemetry)**: Implemented `StageTracer` in `agnivani/observability.py`. Pipeline stage timings in evidence trails and `pipeline_log` now record measured wall-clock millisecond durations (`ms > 0`), eliminating all synthetic `"ms": 0` entries.
- **D6, D7 (Removed frontend fake data)**: Increased snapshot timeout in `js/app.js` from 3s to 20s. Demo simulation mode is strictly opt-in via `?demo=1` with a persistent red banner `⚠ SIMULATED DATA — NOT LIVE`. Replaced `Math.random()` simulation with deterministic fixtures (`js/fixtures/demo_detections.json`). Added live status indicator (`LIVE`/`STALE`/`OFFLINE`) and last ingest clock bound to SSE heartbeat. Snapshot endpoint returns explicit empty state on cold start with `X-Agnivani-Mode` header.
- **D10 (Honest registry sources)**: Removed the fake `_fetch_bhuvan()` stub from `scripts/build_registry.py` and cleaned up references to unintegrated Bhuvan endpoints across `README.md`.
- **D13 (CORS allowlist & token auth on mutating routes)**: Replaced `allow_origins=["*"]` with `cors_origins_list` derived from `CORS_ALLOW_ORIGINS` (default localhost allowlist). Added `AGNIVANI_API_TOKEN` bearer-token dependency (`verify_mutation_token`) on `POST /api/dispatch` with non-blocking startup warnings when unconfigured.

### Added
- `agnivani/models/severity.py`: Pure, physics-based severity determination.
- `agnivani/observability.py`: `StageTracer` for high-resolution stage telemetry.
- `agnivani/api/auth.py`: Token authentication dependency for mutating endpoints.
- `js/fixtures/demo_detections.json`: Deterministic fixtures for offline rehearsal.
- `tests/test_severity.py`: Unit tests for severity invariants, purity, and confidence independence.
- `tests/test_scorer.py`: Tests for `UNRESOLVED` class, context column guards, and verbatim `AV-8A95CFFE` attribution.
- `tests/test_observability.py`: Verification of non-zero wall-clock stage telemetry.

## [Phase 1] - Real AI & Land-Cover Hardening (2026-09-24)

### Fixed
- **D2 (ESA WorldCover 10m integration & WILD reachability)**: Created `agnivani/geo/landcover.py` with 11-code `WORLDCOVER_CLASSES` mapping to the 8 canonical land-cover classes. Integrated AWS S3 Cloud-Optimized GeoTIFF (COG) streaming via range requests and spatial index (`shapely.STRtree`) over cached local tiles under `data/raw/worldcover`. Integrated 3x3 pixel majority voting. Clustered sources and feature tables now carry resolved `landcover_class` and explicit `landcover_status` (`"resolved"` or `"unavailable"`). The `WILD` rule branch is now reachable, and forest fires are correctly segregated from industrial sources.
- **D5 (Schema-valid training set & trained models)**: Created `scripts/materialise_training_set.py` to materialize schema-valid `data/processed/labelled.parquet` containing all 37 `FEATURES` plus `cls` and `block_id`. Executed `agnivani/models/train` end-to-end to generate `data/models/model.joblib` (`XGBClassifier`), `calibrator.joblib` (`CalibratedClassifierCV`), `conformal.json` (calibrated conformal quantile `q`), and `metrics.json`.
- **D9 (Calibrated conformal prediction intervals)**: Replaced the fixed `conf ± 0.12` heuristic band with calibrated non-conformity quantiles computed on held-out spatial blocks at 90% coverage level. Surfaced measured `coverage_pct` in `/api/stats` and `metrics.json`.
- **D14 (SHAP explainability & loud fallback)**: Integrated `shap.TreeExplainer` into `XGBScorer`. Populated `top_features[].contribution` with real signed SHAP feature contributions (top 3 by magnitude), eliminating hardcoded `0.0`. Gated missing artifact loading with loud structlog error logs and explicit `scorer.mode = "fallback"` and `scorer.disclosure` reporting on `/api/health`.

### Added
- `agnivani/geo/landcover.py`: ESA WorldCover 10m land-cover resolver using COG range requests, STRtree spatial indexing, 3x3 window majority voting, and offline degradation.
- `scripts/materialise_training_set.py`: Materialization of schema-valid training set with atomic disk writes.
- `data/models/model.joblib`: Trained production XGBoost classifier (300 estimators, depth 6, lr 0.05).
- `data/models/calibrator.joblib`: Calibrated classifier.
- `data/models/conformal.json`: Calibrated conformal prediction quantile (`q = 0.0206`).
- `data/models/metrics.json`: Spatial-block cross-validation metrics (accuracy: 98.69%, macro-F1: 98.61%, conformal coverage: 100.0%, 39 spatial blocks).
- `tests/test_landcover.py`: Verification of 11-code mapping, tile math, offline fallback, online forest coordinate resolution, and WILD rule branch reachability.
- `tests/test_training.py`: Tests for materialization column contract, 4 emitted artifacts, real non-null metrics, XGBScorer loading, loud fallback disclosure, and real SHAP contributions.

