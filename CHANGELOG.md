# Changelog

All notable changes to the AGNIVANI project will be documented in this file.

## [Phase 2] - Demo-Readiness Execution (P1–P8) (2026-09-25)

### Added
- **P7: Automated Operational Preflight & Makefile**:
  - Created standalone Python verification script `scripts/preflight.py` verifying 6 core subsystems: Python dependencies, model artifacts, geospatial registries, Planck/Dozier solver convergence, ESA WorldCover engine, and DuckDB hero detections.
  - Implemented `GET /api/preflight` diagnostic endpoint in `agnivani/api/pipeline.py`.
  - Created high-contrast, mission-grade `preflight.html` status matrix dashboard with live auto-refresh.
  - Created root `Makefile` implementing standardized operational targets: `install`, `serve`, `test`, `lint`, `preflight`, `run-pipeline`, `demo`, `record`.
- **P8: Containerization & Deployment Readiness**:
  - Created multi-stage `Dockerfile` (Python 3.11-slim) with non-root security user `agnivani` (UID 1001), runtime GDAL/libgomp dependencies, container healthcheck against `/api/preflight`, and entrypoint running Uvicorn.
  - Created `.dockerignore` excluding `.git`, `.venv`, cache files, and development artifacts.
  - Implemented read-only database mode in `agnivani/store/duck.py` via `AGNIVANI_READONLY_DB=1` environment variable, opening DuckDB in read-only mode and guarding mutating methods against unauthorized write attempts.
- **P5: Provenance Transparency (B7)**:
  - Implemented `GET /api/provenance` returning active FIRMS dataset metadata, sensor constellation, temporal window, cluster counts, Dozier convergence rate, and regulatory disclosures.
  - Added clickable provenance chip `#provenance-chip` and `#provenance-bundle-name` in application header.
  - Added dedicated "Data & limits" card (`#data-limits-card`) displaying Condition C2 empirical threshold disclosure, Condition C3 candidate leak framing, and Condition C4 deliberately unattributed count.
  - Created regression suite in `tests/test_corridor_hero.py`.
- **P3: End-to-End Real Ingestion Pipeline (B5)**:
  - Added `POST /api/pipeline/run` and `GET /api/pipeline/runs` in `agnivani/api/pipeline.py` with multi-stage wall-clock performance tracking across all 6 pipeline stages.
  - Broadcasted live `pipeline_stage` SSE events with real millisecond timings.
  - Integrated execution visualizer `#pipeline-live-progress` in `#csv-modal` showing live checkmarks and measured durations.
  - Created `scripts/run_pipeline.py` CLI runner for automated pipeline testing and video recording.
  - Added tests in `tests/test_pipeline_runner.py`.

### Changed & Fixed
- **P1: Decoupled Land-Cover Resolution & B3 Fix**:
  - Completely decoupled `_coarse_landcover` heuristic fallback from `resolve_landcover` in `agnivani/geo/landcover.py`. Offline fallback returns `("unknown", "unavailable")` honestly; never returns fabricated cropland or urban classes.
  - Added invariant tests in `tests/test_landcover.py` verifying that no non-unknown land-cover class is ever paired with `"unavailable"` status.
- **P2: Repaired DOM Contract (B2, B8, B10)**:
  - Added `#inspection-panel`, `#unreachable-banner`, `#demo-banner`, and `#pipeline-live-progress` to `index.html`.
  - Implemented strict `mustEl(id)` DOM contract lookup function in `js/app.js` that logs errors and fails fast if any required element is missing.
  - Quarantined all mock demo fixtures to `js/fixtures/SIMULATED_demo_detections.json`, ensuring zero mock data is present in production bundles.
  - Created `tests/test_dom_contract.py` verifying DOM element IDs, inspection panel presence, and quarantined fixtures.
- **P4: Gujarat Corridor Map & Hero Detections (B6)**:
  - Re-anchored Leaflet satellite map center to Gujarat corridor `[21.8, 71.5]` at zoom 8.
  - Added `?focus=<detection_id>` deep-link URL parameter support with automatic selection and smooth `flyTo` camera animation.
  - Added Corridor vs. All filter buttons (`#filter-corridor-btn`, `#filter-all-btn`) with live unattributed badge (`#unresolved-count-badge`).
  - Added quick-focus chips for hero anomalies (`#hero-flare-1-btn`, `#hero-flare-2-btn`, `#hero-leak-btn`).
- **P6: Sentinel-2 Multispectral Fusion Roadmap (B9)**:
  - Replaced misleading before/after stock photo swipe with an honest Sentinel-2 optical/IR multispectral fusion roadmap panel (retained hidden container for DOM contract compatibility).

## [Phase 0 - Update] - Geocode Correction, Dozier Background & Narrow Fallback (2026-09-24)

### Fixed
- **Option B (Facility Geocode Correction & Per-Facility Match Radius)**:
  - Corrected `Hazira LNG/Steel` in `agnivani/geo/registry.py` from gate/office node `(21.13, 72.64)` to `(21.1055, 72.6405)`, the empirical centroid of the continuous thermal cluster observed across VIIRS passes (21.099–21.114 N, 72.632–72.653 E).
  - Added optional `match_radius_m` field to `Facility` dataclass with a 3500 m override for Hazira LNG/Steel to encompass the contiguous industrial complex (AM/NS Steel, Reliance, Shell LNG, ONGC).
  - Global default match radius remains strictly 2000 m via `FACILITY_MATCH_RADIUS_M` in `agnivani/config.py` (not raised globally to prevent misassociating crop-residue fires).
- **Option D (Dozier Independent Background Estimation)**:
  - Fixed background temperature formulation in `agnivani/physics/planck.py` and `agnivani/geo/cluster.py`: replaced self-background ($T_{bg} = T_{TIR}$) which forced $L_5 - B_{5b} = 0$ and caused 100% `NO_ROOT` failures.
  - Implemented prioritized background estimation: (a) 5th-percentile $T_{TIR}$ for cluster observations when $N \ge 3$; (b) median $T_{TIR}$ of low-FRP ($< 5\text{ MW}$) ambient detections in the pass; (c) pixel's own $T_{TIR}$ flagging `"BACKGROUND_UNAVAILABLE"` with $T_{fire} = \text{null}$.
  - Added unit tests in `tests/test_planck.py` verifying single-pixel retrieval with independent background and explicit flag on self-background.
- **Option C (Narrow Evidence Fallback)**:
  - Added explicit, non-silent fallback rule in `HeuristicScorer` for unresolved Dozier retrievals: when $T_{fire}$ is null but $FRP_{max} \ge 25\text{ MW}$, $night\_frac \ge 0.70$, $dist \le 3500\text{ m}$, and sector in `{REFI_GAS, POWER, STEEL}`, classify as `FLARE` with confidence 0.60 and reason `"Dozier unresolved (background_unavailable); classified on radiative power + nocturnal persistence + facility proximity"`.
- **P0.3 Checkpoint Resolution & Governance (C1, C2, C3)**:
  - *Checkpoint Resolution (C1)*: Formally authorized by user to proceed past the P0.3 gate (UNRESOLVED 87.8% > 60%; FLARE+IND_FIRE = 2 < 5). The 4 facility-matched detections at 492–1372 m and 2 Dozier-retrieved flares at Hazira confirm real operational detection, while the 36 UNRESOLVED detections represent non-industrial thermal activity (crop residue) deliberately unattributed. Moving forward, when any verification gate trips, execution will halt immediately for user confirmation.
  - *Empirical Threshold Disclosure (C2)*: Formally documented that `FLARE` threshold $T_{\text{fire}} \ge 450\text{ K}$ is "empirically derived from a 5-day corridor sample (n=29); to be re-derived as more data arrives." It is an operational retrieval threshold for 375m mixed pixels, not a physical constant.
  - *Candidate Leak Framing (C3)*: Detections `AV-07D8247D` and `AV-EF7A2C35` are explicitly classified as `"candidate fugitive thermal anomaly - low confidence"` at conf 0.55. UI and reason strings display the 0.55 confidence score prominently and prohibit calling these confirmed leaks.
- **Test Artifact Isolation**:
  - Isolated `test_train_writes_four_artifacts` in `tests/test_training.py` using `pytest` fixture `tmp_path`, preventing pytest from clobbering production model artifacts in `data/models/`.

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

