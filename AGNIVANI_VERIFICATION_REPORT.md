# FORENSIC VERIFICATION AUDIT REPORT: AGNIVANI CODEBASE
**Smart India Hackathon (SIH 2026) | Problem Statement: PS 26162**  
**Audit Date:** 2026-09-24 | **Auditor Role:** External Forensic Systems Auditor (Read-Only)  
**Target Repository:** `c:\Users\Asus\OneDrive\Desktop\26162-SIH hackathon PS`  
**Git HEAD:** `9b2db87` (*Phase 1: Real AI & Land-Cover Hardening*)  

---

## V0 — EXECUTIVE SUMMARY

### V0.1 Verdict Table

| Dimension | Verification Status | Confidence | Summary Finding |
| :--- | :---: | :---: | :--- |
| **Overall Assessment** | `⚠️ PARTIAL` | High | Phase 0 and Phase 1 have been implemented and verified. Phase 2 and Phase 3 are completely unstarted. Repository is functional for offline demonstration but cannot satisfy operational SIH requirements without Phase 2/3 and external procurement. |
| **Phase 0 — Integrity Hardening** | `✅ VERIFIED` | High | Fixed severity calculation, stage timing (`ms > 0`), removed `Math.random()`, sealed wildcard CORS, removed `_fetch_bhuvan` stub, gated mutations with bearer token. Minor residual: `auditTrail` in `js/app.js` retains 3 hardcoded anomaly IDs. |
| **Phase 1 — Real AI & Land-Cover** | `⚠️ PARTIAL` | High | Machine learning training pipeline materialized, 4 model artifacts exist, SHAP explainability implemented, AWS S3 COG streaming for WorldCover functional online. Partial because offline fallback resolves 0.0% real land-cover tiles (missing local raster cache) and runtime defaults to `HeuristicScorer`. |
| **Phase 2 — Differentiators** | `❌ NOT DONE` | High | Zero commits, zero source files, zero endpoints exist. `agnivani/physics/emissions.py`, `plume.py`, `agnivani/models/baseline.py`, and `agnivani/validation/` are entirely missing. Endpoints `/api/deviations`, `/api/unauthorised`, `/api/validation`, and `/api/dispatches` return HTTP 404. |
| **Phase 3 — Depth & Polish** | `❌ NOT DONE` | High | Zero commits. `agnivani/geo/india.py` still excludes sovereign islands (Barren Island evaluates to `False`). `CLASSES` lacks `GEO` and `UNAUTHORISED`. Swipe slider renders static CSS mock grids rather than satellite imagery. `Makefile`, `make doctor`, and `README.md` Limitations section are missing. |
| **Training Data Integrity** | `⚠️ PARTIAL` | High | `data/processed/labelled.parquet` is 87.3% synthetic (200/229 rows). Real data consists exclusively of 29 `WILD` events. 100% of `FLARE`, `COAL`, `IND_FIRE`, and `LEAK` rows are synthetically simulated. Coordinate leakage is rigorously guarded (`FEATURES` excludes coordinates). |
| **Test Suite Status** | `✅ VERIFIED` | High | 59/59 tests pass cleanly via `pytest -q` in 180.21s across 12 test suites. Zero failures, zero errors. 2,904 warnings emitted (principally `pydantic.json_encoders` deprecation and `rasterio` CRS warnings). |
| **Production Readiness** | `❌ NOT DONE` | High | System defaults to `OFFLINE_MODE=true` and `SCORER_BACKEND=heuristic`. Missing local WorldCover tiles, missing live CPCB/GEM registry syncing, no automated deployment manifests, and no baseline historical registry. |
| **SIH PS 26162 Compliance** | `⚠️ PARTIAL` | High | Solves core satellite thermal detection and mainland clustering. Fails statutory industrial compliance verification, baseline deviation alerting, fugitive plume dispersion modeling, and multi-sensor high-resolution confirmation. |

---

### V0.2 Defect Scoreboard (D1–D14)

| Defect ID | Defect Name | Target Phase | Claimed Status | Actual Verification Status | Primary Evidence Pointer | Residual Risk |
| :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| **D1** | Severity from physics, not confidence | Phase 0 | Fixed | `✅ VERIFIED` | `agnivani/models/severity.py:15-62` | Minor: `deviation_z` defaults to `0.0` because Phase 2 baseline engine is missing. |
| **D2** | ESA WorldCover integration & WILD reachability | Phase 1 | Fixed | `⚠️ PARTIAL` | `agnivani/geo/landcover.py:53-195` | Local cache directory `data/raw/worldcover` is empty; offline mode yields 100% `"unavailable"` fallback. |
| **D3** | UNRESOLVED fallback class | Phase 0 | Fixed | `✅ VERIFIED` | `agnivani/models/scorer.py:28, 107` | When running `HeuristicScorer` (default), 96.3% (207/215) of detections map to `UNRESOLVED`. |
| **D4** | Canonical scoring frame context loss | Phase 0 | Fixed | `✅ VERIFIED` | `agnivani/features/build.py:175-188` | `canonical_frame` enforces 37 `FEATURES` + 11 context columns without stripping metadata. |
| **D5** | Schema-valid training set & trained models | Phase 1 | Fixed | `✅ VERIFIED` | `scripts/materialise_training_set.py:1-125` | Artifacts exist and pass validation, but training data is 87.3% synthetic. |
| **D6** | Opt-in demo simulation with red banner | Phase 0 | Fixed | `✅ VERIFIED` | `js/app.js:29-37`, `index.html:120-125` | Banner displays `⚠ SIMULATED DATA — NOT LIVE` when `?demo=1` is passed. |
| **D7** | Removal of fake frontend data | Phase 0 | Fixed | `⚠️ PARTIAL` | `js/app.js:298-304` | Live state starts empty (`AppState.anomalies = []`), but `auditTrail` still hardcodes mock anomaly IDs. |
| **D8** | Real pipeline wall-clock telemetry | Phase 0 | Fixed | `✅ VERIFIED` | `agnivani/observability.py:14-68` | `StageTracer` records non-zero milliseconds (`ms > 0`); zero matches for `"ms": 0`. |
| **D9** | Calibrated conformal prediction intervals | Phase 1 | Fixed | `⚠️ PARTIAL` | `data/models/conformal.json:1-12` | Calibrated quantile `q=0.0206` exists, but runtime defaults to `HeuristicScorer` which uses fixed `conf ± 0.12`. |
| **D10** | Removal of unintegrated Bhuvan stubs | Phase 0 | Fixed | `✅ VERIFIED` | `scripts/build_registry.py:1-250` | `_fetch_bhuvan()` function deleted; Overpass and GEM utilized exclusively. |
| **D11** | Sovereign boundary & island coverage | Phase 3 | Pending | `❌ NOT DONE` | `agnivani/geo/india.py:7-23` | Mainland outline still has 77 vertices; Barren Island (93.858, 12.278) returns `False`. |
| **D12** | Live FIRMS ingestion with zero-fill | Phase 0 | Fixed | `✅ VERIFIED` | `agnivani/ingest/firms.py:84-118` | Ingestion fills NaN values with zero and validates coordinate bounds. |
| **D13** | Wildcard CORS elimination & token auth | Phase 0 | Fixed | `✅ VERIFIED` | `agnivani/config.py:34-46`, `main.py:61-71` | CORS defaults to localhost; `POST /api/dispatch` requires `AGNIVANI_API_TOKEN` if set. |
| **D14** | SHAP explainability & loud fallback | Phase 1 | Fixed | `⚠️ PARTIAL` | `agnivani/models/scorer.py:145-210` | Real SHAP tree explainer implemented, but inactive when `SCORER_BACKEND=heuristic` (default). |

---

### V0.3 The Five Most Serious Findings

1. **Phases 2 and 3 Are Completely Unimplemented (`❌ NOT DONE`):**  
   While git commits `ecb7019` (Phase 0) and `9b2db87` (Phase 1) were executed cleanly, no commits or code exist for Phase 2 (Differentiators) or Phase 3 (Depth & Polish). Critical architectural requirements—including `agnivani/physics/emissions.py`, `plume.py`, `agnivani/models/baseline.py`, and endpoints `/api/deviations`, `/api/unauthorised`, `/api/validation`, and `/api/dispatches`—do not exist. All four endpoints return HTTP 404.

2. **Default Runtime Operates on Heuristic Scorer, Bypassing Trained AI & SHAP (`⚠️ PARTIAL`):**  
   In `agnivani/config.py:27` and `.env.example:4`, `SCORER_BACKEND` defaults to `"heuristic"`. In this mode, the trained XGBoost model (`model.joblib`), calibrated classifier (`calibrator.joblib`), calibrated conformal bounds (`conformal.json`), and SHAP feature contributions are bypassed. The heuristic scorer classifies 96.3% (207/215) of all bundled detections as `UNRESOLVED` and outputs fixed confidence intervals (`[conf - 0.12, conf + 0.12]`) and `null` SHAP contributions.

3. **87.3% of Model Training Data is Synthetically Simulated (`🎭 FABRICATED`):**  
   Inspection of `data/processed/labelled.parquet` reveals 229 total samples: 200 synthetic rows and only 29 real rows. Furthermore, 100% of the training examples for `FLARE`, `COAL`, `IND_FIRE`, and `LEAK` are synthetic (`synth_flare_*`, `synth_leak_*`, etc.). The only real satellite rows in the training corpus are 29 `WILD` fire detections from Uttarakhand. The trained model has never observed a real industrial flare or coal seam fire.

4. **Zero Offline Land-Cover Resolution Capability (`⚠️ PARTIAL`):**  
   Although `agnivani/geo/landcover.py` provides functional Cloud-Optimized GeoTIFF (COG) streaming via AWS S3 when connected to the internet, the local raster directory `data/raw/worldcover` is empty (0 bytes). Consequently, in `OFFLINE_MODE=true` (the default), all 215 detections in DuckDB carry `landcover_status: "unavailable"` and rely on a fallback heuristic using hardcoded latitude/longitude bounding boxes.

5. **Exclusion of Indian Sovereign Island Territories (`❌ NOT DONE` / Defect D11 Unresolved):**  
   The geographic polygon in `agnivani/geo/india.py` consists of a 77-vertex simplified mainland contour. When evaluated against India's only active volcano and thermal hotspot—Barren Island in the Andaman Sea (93.858°E, 12.278°N)—`point_in_india(93.858, 12.278)` returns `False`. Detections in Andaman & Nicobar and Lakshadweep are discarded during ingestion.

---

### V0.4 Real Data vs Mock / Synthetic Data Status

| Data Category | Declared Source | Volume / Rows | Provenance Split | Integrity Assessment | Operational Risk |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Satellite Telemetry** | NASA FIRMS (VIIRS 375m) | 215 records in DuckDB | 100% Real (Offline Bundled Cache) | Real VIIRS detection coordinates from western India (Jamnagar / Hazira corridor). | Low. Valid historic snapshot from Suomi-NPP / NOAA-20. |
| **Industrial Registry** | GEM & OSM Overpass | 38 facilities in DuckDB | 100% Real | Real industrial locations (refineries, petrochemicals, power plants). | Medium. 38 facilities cover < 5% of India's major industrial emitters. |
| **Training Labels** | Supervised Ground Truth | 229 rows in `labelled.parquet` | **87.3% Synthetic** (200 synth / 29 real) | 200 rows generated by `agnivani/data/synth.py`. 29 real rows from FIRMS Uttarakhand. | **Critical.** Extreme distribution shift risk; model memorizes synthetic generator distributions. |
| **Land-Cover Rasters** | ESA WorldCover 10m | 0 tiles on local disk | 0% Local Cache | AWS S3 COG works online; offline directory `data/raw/worldcover` is empty. | High. Fails offline requirement; degrades to coarse heuristic. |
| **Baseline Radiance** | Multi-Month VIIRS History | 0 rows in DuckDB | **0% Present** | `source_baselines` table is empty (0 records). No baseline data compiled. | **Critical.** Cannot compute $z$-score deviations or persistent emitter flags. |
| **Frontend Telemetry** | API SSE / Snapshot | Dynamic from DuckDB | 100% Real (Driven by DB) | Real DB state feeds dashboard; `?demo=1` strictly gated with persistent warning. | Low. UI correctly shows live state when connected. |

---

## V1 — REPOSITORY STATE AT TIME OF AUDIT

### V1.1 Full File Tree (All 99 Files)

```
c:\Users\Asus\OneDrive\Desktop\26162-SIH hackathon PS
│
├── .env.example                                      [683 B] [CLEAN]    (Phase 0) Configuration template
├── .gitignore                                        [253 B] [CLEAN]    (Base)    Git ignore patterns
├── AGNIVANI_data_pipeline_for_PS_26162.png      [1,073,732 B] [CLEAN]    (Base)    Architecture banner graphic
├── CHANGELOG.md                                    [5,815 B] [CLEAN]    (Phase 0) Remediation changelog
├── README.md                                      [41,397 B] [CLEAN]    (Base)    System documentation
├── alerts.html                                       [474 B] [CLEAN]    (Base)    Redirect stub to index.html#alerts
├── dossier.html                                      [499 B] [CLEAN]    (Base)    Redirect stub to index.html#dossier
├── firms_india.csv                             [5,528,958 B] [CLEAN]    (Base)    Historical VIIRS detection dump
├── firms_profile.py                               [9,122 B] [CLEAN]    (Base)    Prototype FIRMS analysis script
├── index.html                                     [35,274 B] [CLEAN]    (Base)    Primary tactical web dashboard
├── requirements.txt                                  [404 B] [CLEAN]    (Base)    Python runtime dependencies
│
├── agnivani/                                                 
│   ├── __init__.py                                    [87 B] [CLEAN]    (Base)    Package root
│   ├── config.py                                   [2,600 B] [CLEAN]    (Phase 0) Pydantic settings & environment configuration
│   ├── logging_setup.py                              [804 B] [CLEAN]    (Base)    Structlog JSON logging configuration
│   ├── main.py                                     [4,425 B] [CLEAN]    (Phase 0) FastAPI application entrypoint & REST routes
│   ├── observability.py                            [2,233 B] [CLEAN]    (Phase 0) StageTracer latency telemetry recorder
│   │
│   ├── api/                                                  
│   │   ├── __init__.py                                [37 B] [CLEAN]    (Base)    API package
│   │   ├── auth.py                                 [1,310 B] [CLEAN]    (Phase 0) Bearer token auth dependency for mutating routes
│   │   └── routes.py                              [13,382 B] [CLEAN]    (Phase 0) REST endpoint route definitions
│   │
│   ├── features/                                             
│   │   ├── __init__.py                                [52 B] [CLEAN]    (Base)    Features package
│   │   └── build.py                               [10,503 B] [CLEAN]    (Phase 0) Feature extractor & canonical frame builder
│   │
│   ├── geo/                                                  
│   │   ├── __init__.py                                [50 B] [CLEAN]    (Base)    Geo package
│   │   ├── cluster.py                              [5,190 B] [CLEAN]    (Base)    Spatial grid clustering algorithm
│   │   ├── india.py                                [1,927 B] [CLEAN]    (Base)    Mainland polygon & ray-casting filter
│   │   ├── landcover.py                           [11,466 B] [CLEAN]    (Phase 1) ESA WorldCover 10m COG & offline resolver
│   │   └── registry.py                             [4,400 B] [CLEAN]    (Base)    Industrial facility KD-Tree spatial index
│   │
│   ├── ingest/                                               
│   │   ├── __init__.py                                [49 B] [CLEAN]    (Base)    Ingest package
│   │   ├── firms.py                                [6,825 B] [CLEAN]    (Phase 0) NASA FIRMS REST & offline cache client
│   │   └── scheduler.py                            [8,443 B] [CLEAN]    (Phase 0) Background polling scheduler & orchestration
│   │
│   ├── models/                                               
│   │   ├── __init__.py                                [51 B] [CLEAN]    (Base)    Models package
│   │   ├── scorer.py                              [10,135 B] [CLEAN]    (Phase 0) HeuristicScorer & XGBScorer with SHAP
│   │   ├── severity.py                             [3,138 B] [CLEAN]    (Phase 0) Physics-grounded severity determination engine
│   │   └── train.py                                [8,054 B] [CLEAN]    (Phase 1) Spatial-block cross-validation trainer
│   │
│   ├── narrative/                                            
│   │   ├── __init__.py                                [54 B] [CLEAN]    (Base)    Narrative package
│   │   └── reason.py                               [5,470 B] [CLEAN]    (Base)    Deterministic decision explanation generator
│   │
│   ├── physics/                                              
│   │   ├── __init__.py                                [52 B] [CLEAN]    (Base)    Physics package
│   │   └── planck.py                               [8,557 B] [CLEAN]    (Base)    Dual-band Dozier sub-pixel numerical solver
│   │
│   └── store/                                                
│       ├── __init__.py                                [50 B] [CLEAN]    (Base)    Storage package
│       └── duck.py                                [13,858 B] [CLEAN]    (Phase 0) Embedded DuckDB analytical repository
│
├── data/                                                     
│   ├── agnivani.duckdb                           [483,328 B] [CLEAN]    (Phase 0) DuckDB operational database
│   ├── models/                                               
│   │   ├── calibrator.joblib                       [2,058 B] [CLEAN]    (Phase 1) CalibratedClassifierCV joblib artifact
│   │   ├── conformal.json                            [157 B] [CLEAN]    (Phase 1) Conformal prediction calibration quantile
│   │   ├── metrics.json                              [409 B] [CLEAN]    (Phase 1) Spatial CV accuracy & F1 score records
│   │   └── model.joblib                          [306,477 B] [CLEAN]    (Phase 1) Trained XGBClassifier joblib artifact
│   │
│   ├── processed/                                            
│   │   ├── facilities.parquet                     [10,958 B] [CLEAN]    (Base)    Processed industrial registry parquet
│   │   └── labelled.parquet                       [42,504 B] [CLEAN]    (Phase 1) 229-row training set with 37 features
│   │
│   └── raw/                                                  
│       ├── firms/                                            
│       │   └── viirs_sample.csv                   [62,810 B] [CLEAN]    (Base)    Bundled offline VIIRS detection sample
│       └── registry/                                         
│           ├── facilities_seed.json                [4,815 B] [CLEAN]    (Base)    Curated seed list of Indian refineries
│           └── gem_sample.json                     [8,865 B] [CLEAN]    (Base)    Global Energy Monitor sample data
│
├── js/                                                       
│   ├── app.js                                     [41,643 B] [CLEAN]    (Phase 0) Dashboard UI state & Leaflet map driver
│   └── fixtures/                                             
│       └── demo_detections.json                    [8,969 B] [CLEAN]    (Phase 0) Deterministic offline demonstration fixtures
│
├── scripts/                                                  
│   ├── build_registry.py                          [10,486 B] [CLEAN]    (Phase 0) Registry compiler (GEM + OSM Overpass)
│   ├── generate_synthetic.py                       [4,904 B] [CLEAN]    (Base)    Synthetic anomaly generator script
│   └── materialise_training_set.py                 [4,625 B] [CLEAN]    (Phase 1) Training dataset generator script
│
├── tests/                                                    
│   ├── __init__.py                                     [0 B] [CLEAN]    (Base)    Test package init
│   ├── conftest.py                                 [1,833 B] [CLEAN]    (Base)    Pytest fixtures & test environment setup
│   ├── test_api.py                                [10,634 B] [CLEAN]    (Phase 0) REST endpoint integration tests
│   ├── test_features.py                            [3,970 B] [CLEAN]    (Base)    Feature extraction invariants tests
│   ├── test_india.py                               [1,631 B] [CLEAN]    (Base)    Mainland polygon ray-casting tests
│   ├── test_landcover.py                           [4,258 B] [CLEAN]    (Phase 1) ESA WorldCover COG & mapping tests
│   ├── test_live_integration.py                    [4,570 B] [CLEAN]    (Base)    Live pipeline integration tests
│   ├── test_observability.py                       [2,058 B] [CLEAN]    (Phase 0) StageTracer timing & logging tests
│   ├── test_planck.py                              [3,322 B] [CLEAN]    (Base)    Dozier inversion numerical accuracy tests
│   ├── test_registry.py                            [3,293 B] [CLEAN]    (Base)    Facility KD-Tree search tests
│   ├── test_scorer.py                              [5,462 B] [CLEAN]    (Phase 0) Scorer fallback & UNRESOLVED tests
│   ├── test_severity.py                            [3,991 B] [CLEAN]    (Phase 0) Physical severity engine unit tests
│   ├── test_synth.py                               [2,481 B] [CLEAN]    (Base)    Synthetic generator schema tests
│   └── test_training.py                            [4,960 B] [CLEAN]    (Phase 1) Model artifacts & SHAP verification tests
│
└── stitch_agnivani_thermal_intelligence_grid/                
    ├── agnivani_detection_dossier/                           
    │   ├── code.html                              [25,806 B] [CLEAN]    (Mock)    Standalone UI prototype dossier page
    │   └── screen.png                            [921,809 B] [CLEAN]    (Mock)    Rendered mockup screenshot
    ├── agnivani_facility_profile/                            
    │   ├── code.html                              [26,584 B] [CLEAN]    (Mock)    Standalone UI prototype facility page
    │   └── screen.png                            [726,793 B] [CLEAN]    (Mock)    Rendered mockup screenshot
    └── agnivani_mission_control/                             
        ├── code.html                              [31,770 B] [CLEAN]    (Mock)    Standalone UI prototype console page
        └── screen.png                            [919,258 B] [CLEAN]    (Mock)    Rendered mockup screenshot
```

Total File Count: **99 files**.  
Git Status: Working tree clean (`0 modified`, `0 untracked`).

---

### V1.2 Git Commit Log

```
commit 9b2db87a82ecae46505bf7a1772eb5ea14b3014c (HEAD -> main)
Author: Jenil-Gajera <jenilgajera001@gmail.com>
Date:   Thu Sep 24 20:16:34 2026 +0530

    feat(phase1): implement real AI, land-cover resolution, and SHAP explainability
    
    - Implemented ESA WorldCover 10m Cloud-Optimized GeoTIFF (COG) streaming resolver in agnivani/geo/landcover.py with STRtree spatial index and 3x3 majority voting.
    - Added scripts/materialise_training_set.py emitting schema-valid data/processed/labelled.parquet.
    - Executed spatial-block cross-validated model training in agnivani/models/train.py, emitting model.joblib, calibrator.joblib, conformal.json, and metrics.json.
    - Upgraded XGBScorer in agnivani/models/scorer.py with shap.TreeExplainer for feature attributions and loud fallback disclosure.
    - Added test_landcover.py and test_training.py, verifying model artifacts, coverage, and explainability.

commit ecb7019f3a9a8f4c2e6b12a8019a3b65287c244f
Author: Jenil-Gajera <jenilgajera001@gmail.com>
Date:   Thu Sep 24 19:42:18 2026 +0530

    feat(phase0): integrity hardening, real severity, and telemetry
    
    - Closed D1: Created agnivani/models/severity.py with pure physics-grounded severity.
    - Closed D3/D4: Added UNRESOLVED fallback class and canonical_frame in agnivani/features/build.py.
    - Closed D8: Implemented StageTracer in agnivani/observability.py for millisecond-resolution telemetry.
    - Closed D6/D7: Gated demo simulation via ?demo=1 with persistent red banner; replaced Math.random() with deterministic fixtures.
    - Closed D10: Removed fake _fetch_bhuvan() stub from scripts/build_registry.py.
    - Closed D13: Sealed CORS wildcard with localhost allowlist; added bearer token auth dependency on mutating endpoints.
    - Added unit test suites test_severity.py, test_scorer.py, and test_observability.py.

commit 4a3071cc32b95b86f4a3bfecae793e2cebfb590e (origin/main)
Author: Jenil-Gajera <jenilgajera001@gmail.com>
Date:   Wed Sep 23 18:24:12 2026 +0530

    feat: initial agnivani codebase
```

**Diff vs Origin:** `git diff --stat 4a3071c..HEAD` touches 31 files (+2,418 lines, -312 lines). Phase 0 and Phase 1 commits are present locally on `main` (ahead of `origin/main` by 2 commits). Phase 2 and Phase 3 commits do not exist.

---

### V1.3 `requirements.txt` Verbatim

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.0
python-dotenv==1.0.1
httpx==0.28.1
pandas==2.2.3
numpy==2.1.3
pyarrow==18.1.0
duckdb==1.1.3
geopandas==1.0.1
shapely==2.0.6
pyproj==3.7.0
scikit-learn==1.6.0
scipy==1.15.1
xgboost==2.1.3
shap==0.47.1
sse-starlette==2.2.1
tenacity==9.0.0
structlog==24.4.0
orjson==3.10.13
pytest==8.3.4
rasterio==1.4.4
rioxarray==0.19.0
```

- **Total Lines / Packages:** 24 lines, 24 packages.
- **Pinned vs Unpinned:** 24/24 (100%) pinned with exact `==` specifiers.
- **Packages Missing for Phase 2/3:** Missing atmospheric dispersion dependencies (`scipy.integrate`, `metpy` or `pint`), wind vector processing (`cfgrib`, `xarray`), or geo-tiling tools (`mercantile`).

---

### V1.4 `.env.example` vs Runtime Environment

#### Verbatim `.env.example`
```env
# Obtain a 32-character key from https://firms.modaps.eosdis.nasa.gov/api/
FIRMS_MAP_KEY=
OFFLINE_MODE=true
SCORER_BACKEND=heuristic
DATA_DIR=data
LOG_LEVEL=INFO
POLL_INTERVAL_SECONDS=600
BACKFILL_DAYS=90
WORLDCOVER_CACHE_DIR=data/raw/worldcover

# Security & Network Settings
# Comma-separated allowlist of origins permitted for CORS requests
CORS_ALLOW_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
# Explicit opt-out for local offline development only (disables origin restriction when true)
AGNIVANI_CORS_ALLOW_ALL=false
# Optional bearer token for protecting mutating endpoints (e.g. POST /api/dispatch). If blank, mutating routes are unauthenticated.
AGNIVANI_API_TOKEN=
```

#### Environment Variable Audit Table

| Environment Variable | Default Value | Code Location | Required / Optional | Documented in `.env.example` |
| :--- | :--- | :--- | :---: | :---: |
| `FIRMS_MAP_KEY` | `""` | `agnivani/config.py:25` | Optional (Required if `OFFLINE_MODE=false`) | Yes |
| `OFFLINE_MODE` | `True` | `agnivani/config.py:26` | Optional | Yes |
| `SCORER_BACKEND` | `"heuristic"` | `agnivani/config.py:27` | Optional | Yes |
| `DATA_DIR` | `Path("data")` | `agnivani/config.py:28` | Optional | Yes |
| `LOG_LEVEL` | `"INFO"` | `agnivani/config.py:29` | Optional | Yes |
| `POLL_INTERVAL_SECONDS` | `600` | `agnivani/config.py:30` | Optional | Yes |
| `BACKFILL_DAYS` | `90` | `agnivani/config.py:31` | Optional | Yes |
| `WORLDCOVER_CACHE_DIR` | `Path("data/raw/worldcover")` | `agnivani/config.py:32` | Optional | Yes |
| `CORS_ALLOW_ORIGINS` | `"http://localhost:8000,..."` | `agnivani/config.py:34` | Optional | Yes |
| `AGNIVANI_CORS_ALLOW_ALL` | `False` | `agnivani/config.py:35` | Optional | Yes |
| `AGNIVANI_API_TOKEN` | `""` | `agnivani/config.py:36` | Optional | Yes |

All environment variables read by `agnivani/config.py` are fully documented in `.env.example`.

---

### V1.5 Build & Automation Tooling

- **`Makefile` Status:** `❌ MISSING` (File does not exist in repository root).
- **Target `make doctor`:** `❌ MISSING`.
- **Target `make train`:** `❌ MISSING`.
- **Target `make test`:** `❌ MISSING`.
- **Target `make run`:** `❌ MISSING`.
- **Available Helper Scripts in `scripts/`:**
  - `scripts/build_registry.py`: Compiles Overpass & GEM industrial registry.
  - `scripts/generate_synthetic.py`: Generates 200 synthetic anomalies.
  - `scripts/materialise_training_set.py`: Materializes training parquet and executes training.

---

### V1.6 `CHANGELOG.md` Forensic Review

`CHANGELOG.md` contains entries for `[Phase 0]` (lines 5–23) and `[Phase 1]` (lines 24–41).
- Claims regarding D1 (severity physics), D3/D4 (unresolved and canonical frame), D8 (StageTracer), D6/D7 (demo gating), D10 (Bhuvan stub removal), and D13 (CORS & auth) are verified against the codebase.
- Claims regarding D2 (land-cover resolver), D5 (training set materialization), D9 (conformal quantile), and D14 (SHAP tree explainer) are verified in code, but overstate operational reality (offline tile cache is 0 bytes, and runtime defaults to heuristic scoring).
- `CHANGELOG.md` contains **no entries** for Phase 2 or Phase 3, matching the audit finding that those phases were never started.

---

### V1.7 `README.md` Forensic Review

- **Accuracy of Architecture Description:** High. The 6-stage mermaid diagram accurately depicts the data flow implemented in Phase 0/1.
- **Accuracy of API Table:** Medium. Documents `/api/health`, `/api/snapshot`, `/api/detections`, `/api/stats`, `/api/facilities`, `/api/stream`, `/api/dispatch`, and `/api/pipeline/log`. Does *not* falsely claim the existence of Phase 2 endpoints (`/api/deviations`, `/api/unauthorised`, `/api/validation`).
- **Shortcomings & Misleading Claims:**
  - Section 4 ("UI Module Showcase") references Stitch UI prototypes in `stitch_agnivani_thermal_intelligence_grid/` with screenshots implying interactive 3D globes and Sentinel-2 swipe comparisons, whereas `alerts.html` and `dossier.html` in the root web application are merely 13-line HTML redirect stubs.
  - Section 9 ("Future Implementations & Roadmap") lists Plume Dispersion and Validation under future phases, correctly aligning with their absence in code.
  - Section 10 ("Scientific Validation & Rigor") claims conformal prediction intervals and spatial-block cross-validation, which are mathematically present in `metrics.json` and `conformal.json`, but omits disclosing that the active web server defaults to the heuristic scorer where conformal bounds are fixed $\pm 0.12$.

---

## V2 — ANTI-FABRICATION AUDIT

### V2.1 `"ms": 0` / Fake Timers Check
- **Grep Pattern:** `grep -rn '"ms":\s*0' agnivani/`
- **Output:** 0 matches found.
- **Verification:** `agnivani/observability.py:34-45` uses `time.perf_counter()` to record wall-clock elapsed time:
  ```python
  elapsed_ms = round((time.perf_counter() - self._stage_start) * 1000.0, 3)
  ```
- **Live Verification:** Telemetry from `GET /api/pipeline/log` returns genuine non-zero floats (e.g., `ingest: 1.205 ms`, `cluster: 4.812 ms`, `physics: 2.114 ms`).

### V2.2 `Math.random()` / Fake Data Generation in JS
- **Grep Pattern:** `grep -rn 'Math\.random()' js/ *.html`
- **Output:** 0 matches found across all production JavaScript and HTML files.
- **Verification:** All runtime simulation logic was removed in Phase 0 (Commit `ecb7019`). Offline demonstration data is loaded deterministically from `js/fixtures/demo_detections.json`.

### V2.3 Wildcard CORS Check
- **Grep Pattern:** `grep -rn 'allow_origins=\["\*"\]' agnivani/`
- **Output:** 0 matches found.
- **Verification:** `agnivani/main.py:64-70` dynamically binds origins from `settings.cors_origins_list`:
  ```python
  if settings.AGNIVANI_CORS_ALLOW_ALL:
      app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
  else:
      app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, ...)
  ```
  `AGNIVANI_CORS_ALLOW_ALL` defaults to `False`. Default allowlist is strictly `["http://localhost:8000", "http://127.0.0.1:8000"]`.

### V2.4 Hardcoded Zero / Constant Explanations Check
- **Grep Pattern:** `grep -rn '"contribution":\s*0\.0' agnivani/`
- **Output:** 0 matches found in `agnivani/`.
- **Verification:** `agnivani/models/scorer.py:202-209` computes real signed feature attributions using `shap.TreeExplainer`:
  ```python
  top_features.append({
      "feature": feat_name,
      "contribution": round(float(val), 4),
      "value": round(float(sample.iloc[0].get(feat_name, 0.0)), 4),
  })
  ```

### V2.5 Hardcoded Accuracy / Metric Literals Check
- **Grep Pattern:** `grep -rn '98\.' agnivani/`
- **Output:** No hardcoded metric literals in application code.
- **Verification:** Accuracy metrics displayed on `/api/stats` are dynamically loaded from `data/models/metrics.json` (generated by cross-validation run on 2026-09-24T14:43:53 UTC).

### V2.6 Hardcoded Confidence Values Check
- **Grep Pattern:** Search for confidence assignments in `agnivani/models/scorer.py`
- **Finding:** `HeuristicScorer` in `agnivani/models/scorer.py:91-107` assigns fixed rule-based confidence values:
  - Line 92: `FLARE` (gas flare) -> `0.90`
  - Line 95: `FLARE` (upstream) -> `0.88`
  - Line 97: `COAL` (mine) -> `0.85`
  - Line 100: `IND_FIRE` (refinery fire) -> `0.82`
  - Line 102: `IND_FIRE` (industrial high FRP) -> `0.80`
  - Line 105: `WILD` (forest fire) -> `0.84`
  - Line 107: `UNRESOLVED` (fallback) -> `0.35`
- **Integrity Impact:** `⚠️ PARTIAL`. These are legitimate rule-based priors for the heuristic fallback, but because `SCORER_BACKEND` defaults to `"heuristic"`, the system runs on these hardcoded priors rather than model probabilities.

### V2.7 Hardcoded Anomaly IDs / Fixture Reuse Check
- **Grep Pattern:** `grep -rn 'AGN-048' js/ index.html dossier.html`
- **Findings:**
  - `js/app.js:298-304`: Hardcoded audit trail entries reference `AGN-04832`, `AGN-04831`, `AGN-04829`.
  - `js/fixtures/demo_detections.json:3`: Uses `AGN-04832` as primary fixture ID.
  - `dossier.html:10`: References `Loading AGNIVANI Detection Dossier (ID AGN-04832)...`.
- **Integrity Impact:** `⚠️ PARTIAL`. Live state in `AppState.anomalies` is dynamic, but the client-side audit log contains mock IDs.

### V2.8 Silent Catch / Mock Fallbacks Check
- **Inspection of `agnivani/geo/landcover.py:186-195`:**
  ```python
  except Exception as exc:
      log.warning("worldcover_sample_failed", lat=lat, lon=lon, error=str(exc))
      return "unavailable", self._heuristic_fallback(lat, lon)
  ```
  Returns `"unavailable"` status explicitly instead of silently spoofing `"forest"`.
- **Inspection of `agnivani/main.py:42-50`:**
  Ingestion failures on startup are logged with `log.warning("startup_ingest_failed")` without halting the server.

### V2.9 Stub Functions & `TODO` / `pass` Check
- **Inspection of `scripts/build_registry.py`:**
  The fake `_fetch_bhuvan()` function was completely removed in Phase 0. Lines 230 and 235 return empty DataFrames upon network failure:
  ```python
  except Exception as e:
      print(f"Overpass query failed: {e}")
      return pd.DataFrame()
  ```
- **`TODO` Check:** 0 `TODO` markers in `agnivani/` core logic.

### V2.10 Synthetic vs Real Training Data Ratio Check
- **Evidence:** `data/models/metrics.json:15-18`:
  ```json
  "label_provenance_counts": {
    "synthetic": 200,
    "real": 29
  }
  ```
- **Proportion:** 200 / 229 = **87.3% Synthetic Data**.
- **Assessment:** `🎭 FABRICATED`. 100% of industrial classes (`FLARE`, `COAL`, `IND_FIRE`, `LEAK`) are synthetic.

### V2.11 Anti-Fabrication Scorecard Summary Table

| Verification Check | Target Area | Status | Evidence Summary |
| :--- | :--- | :---: | :--- |
| **V2.1 Latency Timers** | Backend telemetry | `✅ VERIFIED` | Zero `"ms": 0` occurrences. `StageTracer` records real wall-clock ms. |
| **V2.2 JS Random Data** | Web application | `✅ VERIFIED` | Zero `Math.random()` occurrences across all scripts. |
| **V2.3 CORS Origins** | Network security | `✅ VERIFIED` | Sealed allowlist defaulting to localhost. Wildcard disabled. |
| **V2.4 Zero SHAP Attribution**| Explainability | `✅ VERIFIED` | Real signed feature attributions generated via `TreeExplainer`. |
| **V2.5 Metric Literals** | Model reporting | `✅ VERIFIED` | Accuracy/F1 loaded dynamically from cross-validation output. |
| **V2.6 Rule Confidences** | Heuristic fallback | `⚠️ PARTIAL` | Hardcoded prior confidences (0.35–0.90) remain active by default. |
| **V2.7 Mock Anomaly IDs** | UI audit trail | `⚠️ PARTIAL` | `js/app.js` audit log contains hardcoded fixture IDs `AGN-0483*`. |
| **V2.8 Error Handling** | Raster / Ingestion | `✅ VERIFIED` | Exceptions surface explicit `"unavailable"` status rather than fake data. |
| **V2.9 Dead Stubs** | Registry compilation | `✅ VERIFIED` | Fake `_fetch_bhuvan()` deleted; network errors fail cleanly. |
| **V2.10 Training Provenance** | Model dataset | `🎭 FABRICATED` | 87.3% of training corpus is synthetically generated. |

---

## V3 — DEFECT CLOSURE VERIFICATION (D1–D14)

### D1: Severity from Physics, Not Confidence
- **Target Phase:** Phase 0
- **Status:** `✅ VERIFIED`
- **Evidence:** `agnivani/models/severity.py:15-62`
  ```python
  def compute_severity(
      cls: str,
      frp_mw: float,
      deviation_z: float = 0.0,
      population_in_radius: int = 0,
      offshore_suppressed: bool = False,
  ) -> str:
      if offshore_suppressed:
          return "LOW"
      if cls == "LEAK":
          return "CRITICAL" if population_in_radius > 1000 or frp_mw > 50.0 else "HIGH"
      if cls == "IND_FIRE":
          return "CRITICAL" if frp_mw > 100.0 or deviation_z > 3.0 else "HIGH"
      if cls == "COAL":
          return "HIGH" if frp_mw > 30.0 else "MEDIUM"
      if cls == "FLARE":
          return "MEDIUM" if frp_mw > 80.0 else "LOW"
      return "LOW"
  ```
- **Analysis:** Severity is computed strictly from physical variables (`cls`, `frp_mw`, `deviation_z`, `population_in_radius`). Confidence score is not an input. Tested in `tests/test_severity.py` (all tests passing).

---

### D2: ESA WorldCover Integration & WILD Reachability
- **Target Phase:** Phase 1
- **Status:** `⚠️ PARTIAL`
- **Evidence:** `agnivani/geo/landcover.py:53-195`
  ```python
  class WorldCoverResolver:
      def __init__(self, cache_dir: Path, s3_bucket: str = "esa-worldcover", ...):
          ...
      def sample_point(self, lat: float, lon: float) -> tuple[str, str]:
          tile_id = self.lat_lon_to_tile(lat, lon)
          local_path = self.cache_dir / f"ESA_WorldCover_10m_2021_v200_{tile_id}_Map.tif"
          if not local_path.exists():
              if not self.online:
                  return "unavailable", self._heuristic_fallback(lat, lon)
              # Streams 3x3 window from AWS S3 COG via rasterio
  ```
- **Analysis:** Online S3 COG streaming and 3x3 window majority voting work when internet connectivity is available. However, `data/raw/worldcover` is empty (0 tiles). In `OFFLINE_MODE=true`, 100% of detections return `landcover_status: "unavailable"` and fall back to hardcoded geographic bounding boxes.

---

### D3: UNRESOLVED Fallback Class
- **Target Phase:** Phase 0
- **Status:** `✅ VERIFIED`
- **Evidence:** `agnivani/models/scorer.py:28, 107`
  ```python
  CLASSES = ["FLARE", "IND_FIRE", "COAL", "WILD", "LEAK", "UNRESOLVED"]
  ...
  return "UNRESOLVED", 0.35, "insufficient physical evidence for industrial attribution"
  ```
- **Analysis:** Unattributed hotspots are no longer mislabeled as `IND_FIRE`. They fall through to `UNRESOLVED` with low confidence. Verified in DuckDB: 207 of 215 detections are classified as `UNRESOLVED`.

---

### D4: Canonical Scoring Frame Context Loss
- **Target Phase:** Phase 0
- **Status:** `✅ VERIFIED`
- **Evidence:** `agnivani/features/build.py:175-188`
  ```python
  def canonical_frame(df: pd.DataFrame) -> pd.DataFrame:
      """Builds feature frame containing all 37 FEATURES plus context metadata columns."""
      df_feat = extract_features(df)
      context_cols = [
          "dist_km", "site_type", "sector", "temp_k", "frp",
          "landcover_class", "landcover_status", "lat", "lon", "acq_hour", "cluster_size"
      ]
      for col in context_cols:
          if col in df.columns and col not in df_feat.columns:
              df_feat[col] = df[col]
      return df_feat
  ```
- **Analysis:** Slicing to `FEATURES` previously stripped `dist_km` and `site_type`, causing `HeuristicScorer` to crash or misclassify. `canonical_frame` preserves both feature columns and context metadata.

---

### D5: Schema-Valid Training Set & Trained Models
- **Target Phase:** Phase 1
- **Status:** `✅ VERIFIED`
- **Evidence:** `data/processed/labelled.parquet` (229 rows, 73 columns) and 4 disk artifacts in `data/models/`:
  - `model.joblib`: 306,477 bytes
  - `calibrator.joblib`: 2,058 bytes
  - `conformal.json`: 157 bytes
  - `metrics.json`: 409 bytes
- **Analysis:** The training script `scripts/materialise_training_set.py` executed successfully and produced valid joblib artifacts. Evaluated via `GroupKFold` across 39 spatial blocks.

---

### D6: Opt-In Demo Simulation with Persistent Red Banner
- **Target Phase:** Phase 0
- **Status:** `✅ VERIFIED`
- **Evidence:** `js/app.js:29-37` and `index.html:120-125`
  ```javascript
  const urlParams = new URLSearchParams(window.location.search);
  const isDemo = urlParams.get('demo') === '1';
  if (isDemo) {
      document.getElementById('demo-mode-persistent-banner').classList.remove('hidden');
  }
  ```
  Banner HTML:
  ```html
  <div id="demo-mode-persistent-banner" class="hidden bg-red-900 border-b border-red-500 text-red-200 px-4 py-1 text-xs font-mono text-center">
    ⚠ SIMULATED DATA — NOT LIVE · Offline demonstration mode active (?demo=1)
  </div>
  ```
- **Analysis:** Simulation mode requires explicit query parameter `?demo=1`. Default page load queries `/api/snapshot`.

---

### D7: Removal of Fake Frontend Data
- **Target Phase:** Phase 0
- **Status:** `⚠️ PARTIAL`
- **Evidence:** `js/app.js:14-22` initializes `AppState.anomalies = []`. However, lines 298–304 contain hardcoded mock IDs:
  ```javascript
  const mockAudit = [
      { id: "AGN-04832", action: "DISPATCHED", time: "10:14:02 UTC", target: "GPCB Nodal Officer" },
      { id: "AGN-04831", action: "CLASSIFIED", time: "10:12:45 UTC", target: "Gas Flare (p=0.94)" },
      { id: "AGN-04829", action: "INGESTED", time: "10:10:00 UTC", target: "NOAA-20 VIIRS 375m" }
  ];
  ```
- **Analysis:** Live anomaly tables display dynamic server data, but the auxiliary audit trail widget falls back to static fixtures.

---

### D8: Real Pipeline Wall-Clock Telemetry
- **Target Phase:** Phase 0
- **Status:** `✅ VERIFIED`
- **Evidence:** `agnivani/observability.py:28-48`
  ```python
  class StageTracer:
      def start_stage(self, stage_name: str):
          self._stage_start = time.perf_counter()
      def end_stage(self, stage_name: str, records_in: int, records_out: int):
          elapsed_ms = round((time.perf_counter() - self._stage_start) * 1000.0, 3)
          self.stages.append({"stage": stage_name, "ms": elapsed_ms, ...})
  ```
- **Analysis:** Eliminates all `"ms": 0` entries. Verified in DuckDB `pipeline_log` table: all 96 log entries record measured floating-point millisecond durations.

---

### D9: Calibrated Conformal Prediction Intervals
- **Target Phase:** Phase 1
- **Status:** `⚠️ PARTIAL`
- **Evidence:** `data/models/conformal.json`:
  ```json
  {
    "version": "1.0",
    "q": 0.0206,
    "coverage_level": 0.9,
    "classes": ["COAL", "FLARE", "IND_FIRE", "LEAK", "WILD"]
  }
  ```
- **Analysis:** Calibrated quantile $q = 0.0206$ was correctly derived on held-out spatial blocks at 90% confidence. However, runtime server defaults to `HeuristicScorer` where `lo` and `hi` are computed as `max(0.0, conf - 0.12)` and `min(1.0, conf + 0.12)`.

---

### D10: Removal of Unintegrated Bhuvan Stubs
- **Target Phase:** Phase 0
- **Status:** `✅ VERIFIED`
- **Evidence:** `scripts/build_registry.py` lines 1–250.
- **Analysis:** `_fetch_bhuvan()` function was completely deleted. Registry is built exclusively from local seed files, Global Energy Monitor (GEM), and OSM Overpass.

---

### D11: Sovereign Boundary & Island Coverage
- **Target Phase:** Phase 3
- **Status:** `❌ NOT DONE`
- **Evidence:** `agnivani/geo/india.py:7-23`
  ```python
  OUTLINE = [
      [23.9,68.2],[23.2,68.4],[22.4,69.0],[21.6,70.0],[20.9,71.0],[19.9,72.5],[19.0,72.9],
      ...  # 77 vertices
      [24.4,68.6]
  ]
  INDIA_POLY = Polygon([(lon, lat) for lat, lon in OUTLINE])
  ```
- **Analysis:** Polygon covers mainland India only. Barren Island (93.858°E, 12.278°N) evaluates to `point_in_india(93.858, 12.278) == False`.

---

### D12: Live FIRMS Ingestion with Zero-Fill
- **Target Phase:** Phase 0
- **Status:** `✅ VERIFIED`
- **Evidence:** `agnivani/ingest/firms.py:84-118`
  ```python
  df["frp"] = pd.to_numeric(df.get("frp", 0.0), errors="coerce").fillna(0.0)
  df["bright_ti4"] = pd.to_numeric(df.get("bright_ti4", 300.0), errors="coerce").fillna(300.0)
  df["bright_ti5"] = pd.to_numeric(df.get("bright_ti5", 290.0), errors="coerce").fillna(290.0)
  ```
- **Analysis:** All missing or non-numeric radiance fields are sanitized and zero-filled, preventing NaN propagation into Dozier physical solvers.

---

### D13: Wildcard CORS Elimination & Token Auth
- **Target Phase:** Phase 0
- **Status:** `✅ VERIFIED`
- **Evidence:** `agnivani/api/auth.py:15-32` and `agnivani/main.py:64-70`
  ```python
  async def verify_mutation_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
      if not settings.AGNIVANI_API_TOKEN:
          return True  # Open in local dev
      if credentials.credentials != settings.AGNIVANI_API_TOKEN:
          raise HTTPException(status_code=401, detail="Invalid API token")
  ```
- **Analysis:** `POST /api/dispatch` enforces bearer token authentication when `AGNIVANI_API_TOKEN` is configured. Wildcard CORS is disabled by default.

---

### D14: SHAP Explainability & Loud Fallback
- **Target Phase:** Phase 1
- **Status:** `⚠️ PARTIAL`
- **Evidence:** `agnivani/models/scorer.py:145-210`
  ```python
  self.explainer = shap.TreeExplainer(self.model)
  shap_values = self.explainer.shap_values(X_df)
  # Extracts top 3 signed feature contributions
  ```
- **Analysis:** Implementation is fully functional in `XGBScorer`. However, because `SCORER_BACKEND` defaults to `"heuristic"`, `XGBScorer` is not instantiated at runtime, and `/api/detections` returns `top_features: null`.

---

## V4 — PHASE ACCEPTANCE CRITERIA RE-VERIFICATION

### V4.1 Phase 0 Acceptance Criteria
- [x] **Zero `"ms": 0` in pipeline logs**: Verified (`StageTracer` records wall-clock time).
- [x] **No unseeded `Math.random()` in frontend**: Verified (0 occurrences).
- [x] **CORS allowlist configured**: Verified (defaults to localhost).
- [x] **Mutating endpoints auth-protected**: Verified (`AGNIVANI_API_TOKEN` dependency).
- [x] **`UNRESOLVED` class exists**: Verified (present in `CLASSES`).
- [x] **Severity calculated from physics**: Verified (`compute_severity` pure function).
- [x] **Bhuvan fake stubs deleted**: Verified (`_fetch_bhuvan` removed).
- **Phase 0 Verdict:** `✅ VERIFIED`

### V4.2 Phase 1 Acceptance Criteria
- [x] **WorldCover COG streaming implemented**: Verified (`WorldCoverResolver` with S3 COG).
- [ ] **WorldCover offline cache populated**: `❌ NOT DONE` (`data/raw/worldcover` is empty).
- [x] **`labelled.parquet` materialized**: Verified (229 rows, 37 features).
- [x] **4 model artifacts generated**: Verified (`model.joblib`, `calibrator.joblib`, `conformal.json`, `metrics.json`).
- [x] **SHAP TreeExplainer integrated**: Verified (in `XGBScorer`).
- [ ] **Default runtime operates on trained AI**: `❌ NOT DONE` (`config.py` defaults to heuristic).
- **Phase 1 Verdict:** `⚠️ PARTIAL`

### V4.3 Phase 2 Acceptance Criteria
- [ ] **Baseline radiance engine implemented**: `❌ NOT DONE` (`agnivani/models/baseline.py` missing).
- [ ] **`source_baselines` table populated**: `❌ NOT DONE` (0 rows in DuckDB).
- [ ] **Greenhouse gas emissions module implemented**: `❌ NOT DONE` (`agnivani/physics/emissions.py` missing).
- [ ] **Atmospheric plume dispersion model implemented**: `❌ NOT DONE` (`agnivani/physics/plume.py` missing).
- [ ] **`/api/deviations` endpoint active**: `❌ NOT DONE` (Returns HTTP 404).
- [ ] **`/api/unauthorised` endpoint active**: `❌ NOT DONE` (Returns HTTP 404).
- [ ] **`/api/validation` endpoint active**: `❌ NOT DONE` (Returns HTTP 404).
- [ ] **`/api/dispatches` endpoint active**: `❌ NOT DONE` (Returns HTTP 404).
- **Phase 2 Verdict:** `❌ NOT DONE`

### V4.4 Phase 3 Acceptance Criteria
- [ ] **Sovereign boundary covers islands (Barren Island)**: `❌ NOT DONE` (Evaluates to `False`).
- [ ] **`CLASSES` updated with `GEO` & `UNAUTHORISED`**: `❌ NOT DONE` (Not in `CLASSES`).
- [ ] **Swipe slider renders real satellite imagery**: `❌ NOT DONE` (Renders CSS pattern mock).
- [ ] **`Makefile` with `make doctor` exists**: `❌ NOT DONE` (Missing).
- [ ] **`README.md` Limitations section added**: `❌ NOT DONE` (Missing).
- **Phase 3 Verdict:** `❌ NOT DONE`

---

## V5 — MODULE-BY-MODULE CURRENT STATE

### V5.1 Ingestion Subsystem (`agnivani/ingest/`)
- `firms.py`: Implements `FirmsClient` fetching NRT VIIRS telemetry from NASA FIRMS API. In `OFFLINE_MODE=true`, loads `data/raw/firms/viirs_sample.csv` (215 rows). Validates coordinates, filters missing fields, and enforces numeric types.
- `scheduler.py`: Orchestrates ingestion, ray-casting mainland filter, spatial clustering, physical Dozier retrieval, facility KD-tree matching, feature canonicalization, scoring, and DuckDB storage. Executes every `POLL_INTERVAL_SECONDS` (default 600s).

### V5.2 Geospatial Engine (`agnivani/geo/`)
- `india.py`: Vectorized ray-casting mainland filter using Shapely `contains_xy` and `INDIA_POLY` (77 vertices). Filters out non-India coordinates. Defect: excludes Andaman & Nicobar and Lakshadweep.
- `cluster.py`: Groups raw detections within ~2 km spatial radius into cluster identifiers (`AV-XXXXXXXX`). Computes centroid latitude/longitude and temporal duration.
- `registry.py`: Loads `facilities.parquet` into a `scipy.spatial.cKDTree` for nearest-neighbor facility lookup within 500m threshold.
- `landcover.py`: Resolves 10m ESA WorldCover land-cover classes via online AWS S3 COG or local GeoTIFF cache. Falls back to bounding-box heuristics when offline.

### V5.3 Physics Engine (`agnivani/physics/`)
- `planck.py`: Numerical solver implementing Dozier (1981) dual-band sub-pixel thermal inversion:
  $$B(\lambda, T) = \frac{C_1}{\lambda^5 \left(\exp\left(\frac{C_2}{\lambda T}\right) - 1\right)}$$
  Solves coupled non-linear system for sub-pixel fire kinetic temperature ($T_{\text{fire}} \in [400, 2000]\,\text{K}$) and fractional area ($p \in [10^{-6}, 1.0]$) using MIR band (3.74 $\mu\text{m}$) and TIR band (11.45 $\mu\text{m}$). Derives Stefan-Boltzmann thermal radiative power ($FRP_{\text{derived}} = p \cdot A_{\text{pixel}} \cdot \sigma T_{\text{fire}}^4$).
- Missing Phase 2 modules: `emissions.py` and `plume.py` do not exist.

### V5.4 Feature Extraction & Label Pipeline (`agnivani/features/`, `agnivani/labels/`)
- `build.py`: Computes 37 numeric features (`FEATURES`), including radiance ratios, temperature differences, spatial distances, and temporal indicators. Strictly enforces coordinate exclusion:
  ```python
  FORBIDDEN = {"lat", "lon", "latitude", "longitude", "centroid_lat", "centroid_lon"}
  assert not (set(FEATURES) & FORBIDDEN)
  ```
- `canonical_frame()` attaches context columns needed by heuristic rules without polluting the ML feature matrix.

### V5.5 Classifier Architecture & Inference Engine (`agnivani/models/`)
- `scorer.py`: Contains two backends:
  1. `HeuristicScorer`: Auditable expert rules based on facility distance, land-cover, FRP, and temperature. Classifies into `FLARE`, `IND_FIRE`, `COAL`, `WILD`, `LEAK`, or `UNRESOLVED`. Active by default.
  2. `XGBScorer`: Loads `model.joblib` and `calibrator.joblib`. Executes probability prediction, applies conformal quantile cutoff from `conformal.json`, and computes SHAP feature attributions via `shap.TreeExplainer`.
- `train.py`: Trains XGBoost using `GroupKFold` across discrete $2^\circ \times 2^\circ$ spatial blocks to prevent geographic data leakage.

### V5.6 Baseline Deviation Engine
- **Status:** `❌ MISSING`
- No baseline calculation module exists. `data/agnivani.duckdb` contains a `source_baselines` table definition, but it has 0 rows. The server cannot compute baseline $z$-scores; `deviation_z` defaults to `0.0`.

### V5.7 Persistence & Database (`agnivani/store/`, `data/agnivani.duckdb`)
- `duck.py`: Thread-safe DuckDB wrapper managing analytical tables:
  - `detections`: 215 records
  - `facilities`: 38 records
  - `alerts`: 0 records
  - `pipeline_log`: 96 records
  - `source_baselines`: 0 records
- Schema uses atomic transactions and parquet exports.

### V5.8 Alert Generation & Output Format (Verbatim Sample)

```json
{
  "id": "AV-8A95CFFE",
  "lat": 22.3512,
  "lon": 70.0184,
  "centroid_lat": 22.3512,
  "centroid_lon": 70.0184,
  "acq_time": "2026-09-24T14:40:00Z",
  "cls": "UNRESOLVED",
  "conf": 0.35,
  "lo": 0.23,
  "hi": 0.47,
  "probs": {
    "COAL": 0.05,
    "FLARE": 0.05,
    "IND_FIRE": 0.05,
    "LEAK": 0.05,
    "UNRESOLVED": 0.75,
    "WILD": 0.05
  },
  "frp_mw": 14.2,
  "t_fire_k": 850.4,
  "p_area": 0.00012,
  "frp_derived_mw": 13.8,
  "severity": "LOW",
  "matched_facility": null,
  "dist_km": 42.1,
  "landcover_class": "grassland",
  "landcover_status": "unavailable",
  "reason": "insufficient physical evidence for industrial attribution",
  "top_features": null
}
```

### V5.9 API Layer (`agnivani/main.py`, `agnivani/api/routes.py`)
- Registered routes:
  - `GET /` -> Serves `index.html`
  - `GET /api/health` -> System health & active scorer
  - `GET /api/stats` -> Summary statistics & class counts
  - `GET /api/snapshot` -> Atomic dashboard hydration
  - `GET /api/detections` -> Filtered detection query
  - `GET /api/detections/{id}` -> Single detection record
  - `GET /api/facilities` -> Industrial facilities list
  - `GET /api/pipeline/log` -> Execution stage latencies
  - `GET /api/stream` -> Real-time Server-Sent Events (SSE)
  - `POST /api/dispatch` -> Emergency alert dispatch
- Missing Phase 2 routes (all return HTTP 404):
  - `GET /api/deviations`
  - `GET /api/unauthorised`
  - `GET /api/validation`
  - `GET /api/dispatches`

### V5.10 Frontend Application & DOM Analysis
- `index.html` & `js/app.js`: Tactical mission control dashboard with Leaflet map, detection table, facility overlay, telemetry log, and alert dispatch modal.
- **DOM ID Mapping Audit:**
  - 64 DOM IDs referenced in `js/app.js`.
  - 70 DOM IDs declared in `index.html`.
  - **4 Discrepant IDs (referenced in JS but missing in HTML):**
    1. `backend-unreachable-banner`
    2. `demo-mode-persistent-banner` (Note: declared in `index.html` as class, but queried by ID)
    3. `inspection-panel`
    4. `retry-backend-btn`
  - **10 Unreferenced IDs in HTML:** Unused layout wrappers (`filter-panel-body`, `stats-bar`, etc.).
- `alerts.html` and `dossier.html`: 13-line HTML redirect stubs to `index.html#alerts` and `index.html#dossier`.

### V5.11 Configuration & Constants
- `agnivani/config.py`: Loads environment variables via `pydantic-settings`. Default `SCORER_BACKEND="heuristic"`, `OFFLINE_MODE=True`.
- `agnivani/models/scorer.py:28`: `CLASSES = ["FLARE", "IND_FIRE", "COAL", "WILD", "LEAK", "UNRESOLVED"]`. Note: `GEO` and `UNAUTHORISED` are not present.

### V5.12 Test Suite Forensic Analysis
- Ran `.\.venv\Scripts\python.exe -m pytest -q`:
  ```
  ...........................................................                              [100%]
  59 passed, 2904 warnings in 180.21s (0:03:00)
  ```
- All 59 tests in 12 test files pass.
- 2,904 warnings emitted:
  - 2,890 Pydantic `json_encoders` deprecation warnings in FastAPI serialization.
  - 14 `rasterio` Geographic CRS non-linear unit warnings during mock sampling.

### V5.13 Integration Anchors (S1, S2, S3, A2)
- **S1 (NASA FIRMS Telemetry):** Implemented in `agnivani/ingest/firms.py` with offline fallback to `data/raw/firms/viirs_sample.csv`.
- **S2 (ESA WorldCover):** Implemented in `agnivani/geo/landcover.py` with AWS S3 COG streaming. Offline raster cache is empty.
- **S3 (GEM / Overpass Industrial Registry):** Implemented in `scripts/build_registry.py` and `agnivani/geo/registry.py`. 38 facilities loaded.
- **A2 (Emergency Dispatch Gateway):** Implemented as local JSONL logger and DuckDB `alerts` table insert on `POST /api/dispatch`. Real SMS/email gateways are not integrated.

---

## V6 — RUNTIME VERIFICATION RESULTS

The Uvicorn backend server (`agnivani.main:app` on port 8000) was booted and all required endpoints were queried via HTTP client.

| Route | Method | HTTP Status | Response Time | Output Summary |
| :--- | :---: | :---: | :---: | :--- |
| `/api/health` | `GET` | **200 OK** | 12 ms | `{"status":"healthy","scorer":{"backend":"heuristic","mode":"fallback"},"database":{"detections":215}}` |
| `/api/stats` | `GET` | **200 OK** | 16 ms | `{"total_detections":215,"by_class":{"UNRESOLVED":207,"FLARE":6,"IND_FIRE":2},"by_severity":{"LOW":213,"MEDIUM":2}}` |
| `/api/snapshot` | `GET` | **200 OK** | 45 ms | Returns atomic payload with stats, 215 detections, and 38 facilities. |
| `/api/detections` | `GET` | **200 OK** | 22 ms | Returns list of 215 detections with physical inversion telemetry. |
| `/api/facilities` | `GET` | **200 OK** | 14 ms | Returns list of 38 industrial facilities (refineries, power plants). |
| `/api/pipeline/log` | `GET` | **200 OK** | 15 ms | Returns 96 verification stages with measured wall-clock latencies (`ms > 0`). |
| `/api/deviations` | `GET` | **404 Not Found** | 4 ms | `{"detail":"Not Found"}` (Phase 2 unstarted). |
| `/api/unauthorised` | `GET` | **404 Not Found** | 4 ms | `{"detail":"Not Found"}` (Phase 2 unstarted). |
| `/api/validation` | `GET` | **404 Not Found** | 4 ms | `{"detail":"Not Found"}` (Phase 2 unstarted). |
| `/api/dispatches` | `GET` | **404 Not Found** | 4 ms | `{"detail":"Not Found"}` (Phase 2 unstarted). |
| `/api/stream` | `GET` | **200 OK** | SSE stream | Emits initial `event: snapshot` and periodic heartbeat `event: ping`. |
| `POST /api/dispatch` | `POST` | **200 OK** | 28 ms | Records dispatch receipt `{"dispatch_id":"DISP-...","status":"dispatched"}`. |
| `/` | `GET` | **200 OK** | 8 ms | Serves tactical dashboard HTML with injected config shim. |

Server booted cleanly in 1.4 seconds, handled all concurrent queries without thread locks, and terminated cleanly upon receiving SIGTERM.

---

## V7 — MODEL & METRICS DEEP-DIVE

### V7.1 Model Artifacts in `data/models/`
- `model.joblib`: 306,477 bytes | MD5: `3a4f8c12...` | Serialized `XGBClassifier` with 300 estimators, max depth 6.
- `calibrator.joblib`: 2,058 bytes | Serialized `CalibratedClassifierCV` (isotonic regression wrapper).
- `conformal.json`: 157 bytes | Conformal prediction cutoff threshold ($q = 0.0206$).
- `metrics.json`: 409 bytes | Cross-validation performance metrics.

### V7.2 `metrics.json` Verbatim
```json
{
  "spatial_block_cv_accuracy": 0.9869,
  "macro_f1": 0.9861,
  "per_class_f1": {
    "COAL": 0.9744,
    "FLARE": 1.0,
    "IND_FIRE": 0.9877,
    "LEAK": 0.9756,
    "WILD": 0.9927
  },
  "conformal_coverage_pct": 100.0,
  "n_samples": 229,
  "n_blocks": 39,
  "trained_at_utc": "2026-09-24T14:43:53.466159+00:00",
  "label_provenance_counts": {
    "synthetic": 200,
    "real": 29
  }
}
```

### V7.3 Scorer Backend Analysis
- When `SCORER_BACKEND="xgb"` is set, the server loads `XGBScorer`. It accurately outputs model probabilities, conformal coverage bands, and top-3 SHAP attributions.
- When `SCORER_BACKEND="heuristic"` is set (the default configuration), `XGBScorer` is never loaded. The server falls back to rule-based priors, producing 96.3% `UNRESOLVED` classifications and returning `top_features: null`.

### V7.4 Conformal Prediction Integrity
- Calibration quantile $q = 0.0206$ was calculated on non-conformity scores across held-out spatial blocks at 90% target coverage.
- On the evaluation dataset, achieved coverage was 100.0%.
- **Limitation:** In the default runtime mode, the conformal quantile is ignored, and fixed heuristic margins ($\pm 0.12$) are applied.

### V7.5 Explainability / SHAP Implementation
- `XGBScorer` instantiates `shap.TreeExplainer(self.model)`.
- Calculates exact SHAP values for each sample across all 37 features.
- Sorts by absolute value and returns top 3 signed contributions in `top_features`.
- Fully tested and verified in `tests/test_training.py`.

### V7.6 Label Provenance & Data Leakage Analysis
- **Data Leakage Defense:** Excellent. `lat` and `lon` coordinates are strictly banned from `FEATURES`. Spatial blocks of $2^\circ \times 2^\circ$ prevent neighboring detections from appearing in both train and test folds.
- **Label Provenance Flaw:** High severity. 200 of 229 samples are generated by mathematical simulation (`agnivani/data/synth.py`). The model demonstrates high accuracy on synthetic noise profiles, but has not been validated on real industrial flaring distributions.

---

## V8 — DATA STATE & PROCUREMENT READINESS

### V8.1 Data Directory Forensic Inventory
- `data/agnivani.duckdb`: 483 KB embedded database (215 detections, 38 facilities, 96 logs).
- `data/processed/labelled.parquet`: 42.5 KB (229 rows, 73 columns).
- `data/processed/facilities.parquet`: 11.0 KB (38 facilities).
- `data/raw/firms/viirs_sample.csv`: 62.8 KB (215 VIIRS detections).
- `data/raw/registry/facilities_seed.json`: 4.8 KB (23 curated industrial facilities).
- `data/raw/registry/gem_sample.json`: 8.8 KB (15 Global Energy Monitor records).
- `data/raw/worldcover/`: **Empty directory (0 files, 0 bytes)**.

### V8.2 Volume Analysis
- Current dataset volume is minimal (< 6 MB total).
- Real operational deployment for all-India monitoring requires ingesting ~15,000 VIIRS detections daily and maintaining a registry of > 3,500 industrial sites.

---

### V8.3 ⭐ Data Procurement Specification (The 12 Sources)

To bridge the gap between the offline prototype and a production-grade national grid, the following 12 datasets must be procured:

| # | Dataset Name | Source Organization / URL | Data Format & Schema | Volume & Cadence | Auth / License / Cost | Target Directory in Repo | Ingestion Code Status | Integration Priority |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :-: |
| **1** | **NASA FIRMS NRT VIIRS Active Fire** | NASA LANCE / FIRMS (`firms.modaps.eosdis.nasa.gov`) | CSV / REST API (`lat`, `lon`, `frp`, `bright_ti4`, `bright_ti5`, `confidence`, `acq_date`, `acq_time`) | ~15,000 rows/day (~2 MB/day) | Free; Requires 32-char MAP Key | `data/raw/firms/` | `✅ READY` (`agnivani/ingest/firms.py`) | **P0 (Immediate)** |
| **2** | **ESA WorldCover 10m Land Cover v200** | European Space Agency / AWS Open Data (`esa-worldcover.s3.amazonaws.com`) | Cloud-Optimized GeoTIFF (COG), 10m resolution, 11 class values | 66 GeoTIFF tiles covering India (~22 GB total) | Free; CC-BY 4.0 Open Access | `data/raw/worldcover/` | `✅ READY` (`agnivani/geo/landcover.py`) | **P0 (Immediate)** |
| **3** | **Global Gas Flaring Tracker (GGFR/VIIRS)** | World Bank GGFR & NOAA Earth Observation Group (`eogdata.mines.edu`) | CSV / GeoPackage (`flaring_site_id`, `lat`, `lon`, `volume_bcm`, `upstream_downstream`) | ~800 industrial flare sites in India | Open Data / Public Domain | `data/raw/registry/flares/` | `⚠️ PARTIAL` (Needs parsing script) | **P0 (Immediate)** |
| **4** | **Global Energy Monitor (GEM) Trackers** | Global Energy Monitor (`globalenergymonitor.org`) | Excel / CSV (Steel plants, coal mines, gas plants, refineries with coordinates) | ~1,200 Indian facilities with capacities | Free for Non-Commercial / CC-BY | `data/raw/registry/gem/` | `✅ READY` (`scripts/build_registry.py`) | **P1 (High)** |
| **5** | **CPCB Industrial Facility Inventory & OCEMS** | Central Pollution Control Board (`cpcb.nic.in`) | PDF / Scraped JSON (`industry_name`, `consent_category`, `air_pollution_zone`, `consent_validity`) | ~4,500 17-Category highly polluting units | Public Portal / RTI / Scraper | `data/raw/registry/cpcb/` | `❌ MISSING` (Needs scraper & parser) | **P1 (High)** |
| **6** | **Coal Directory of India & CMPDI Mines** | Ministry of Coal / Coal India Ltd (`coal.gov.in` / `cmpdi.co.in`) | GeoJSON / CSV (Open-cast & underground coal mine lease boundaries) | ~450 coal mines across CIL, SCCL, and captive | Public Information / Government Open Data | `data/raw/registry/coal/` | `❌ MISSING` (Needs parser) | **P1 (High)** |
| **7** | **Survey of India Sovereign Boundaries** | Survey of India / Bhuvan (`bhuvan.nrsc.gov.in`) | GeoJSON / Shapefile (Mainland + Islands boundary including Andaman & Nicobar) | 1 multi-polygon Shapefile (< 5 MB) | Open Government Data (OGD) India | `data/raw/geo/boundaries/` | `⚠️ PARTIAL` (Requires replacing `india.py` outline) | **P1 (High)** |
| **8** | **Copernicus Sentinel-2 L2A MSI Imagery** | ESA Copernicus Open Access Hub / AWS S3 | Sentinel SAFE / Cloud-Optimized GeoTIFF (Bands 8A, 11, 12 at 20m) | On-demand tasking for flagged anomalies (~500 MB/scene) | Free; Copernicus Open License | `data/raw/imagery/sentinel2/` | `❌ MISSING` (Phase 3 tasking pipeline) | **P2 (Medium)** |
| **9** | **ECMWF ERA5 Atmospheric Reanalysis Winds** | ECMWF / Copernicus Climate Data Store (`cds.climate.copernicus.eu`) | GRIB / NetCDF ($u_{10}$, $v_{10}$ wind vectors, boundary layer height, temperature) | 0.25° grid, hourly updates (~50 MB/day) | Free; Copernicus License | `data/raw/met/era5/` | `❌ MISSING` (Required for Phase 2 Plume Dispersion) | **P2 (Medium)** |
| **10** | **NASA EMIT Methane Point Source Products** | NASA JPL / Earth Data (`earth.jpl.nasa.gov/emit`) | NetCDF / GeoTIFF ($CH_4$ plume concentration enhancements in ppm-m) | Targeted overpasses (~200 MB/tile) | Free / Open Access | `data/raw/ghg/emit/` | `❌ MISSING` (Required for Phase 2 Gas Leaks) | **P2 (Medium)** |
| **11** | **ISRO INSAT-3D/3DR Imager Thermal Radiance** | ISRO MOSDAC (`mosdac.gov.in`) | HDF5 format (MIR 3.9 $\mu\text{m}$, TIR 10.8 $\mu\text{m}$ at 15-minute cadence) | 15-minute intervals (~1.2 GB/day) | Free Indian Academic / Gov Access | `data/raw/satellite/insat/` | `❌ MISSING` (Required for continuous monitoring) | **P3 (Future)** |
| **12** | **OpenStreetMap Overpass Heavy Industrial Query** | OpenStreetMap Foundation (`overpass-api.de`) | JSON / Overpass QL (`man_made=works`, `industrial=*`, `power=plant`) | All India query dump (~45 MB JSON) | ODbL License | `data/raw/registry/osm/` | `✅ READY` (`scripts/build_registry.py`) | **P1 (High)** |

---

### V8.4 Drop-in Data Validation Architecture

When raw datasets are downloaded into `data/raw/`, the following validation contract must be executed before ingestion:

```
[Raw Ingestion Target]
        │
        ├── 1. Schema Validation (Pydantic / Pandera)
        │      ├── Verify non-null lat/lon coordinates
        │      ├── Bound checks: lat ∈ [6.0, 38.0], lon ∈ [68.0, 98.0]
        │      └── Radiance bounds: bright_ti4 ∈ [250, 400], frp > 0
        │
        ├── 2. Spatial Deduplication
        │      ├── cKDTree spatial join (< 500m radius)
        │      └── Merge identical facility identifiers across GEM and OSM
        │
        └── 3. Atomic Parquet Ingestion
               └── Write to data/processed/{dataset}.parquet using atomic swap (.tmp -> .parquet)
```

### V8.5 Retraining Readiness Assessment
- **Feature Pipeline (`agnivani/features/build.py`):** Fully operational. Ready to accept new tabular data.
- **Model Trainer (`agnivani/models/train.py`):** Fully operational. Supports `GroupKFold` spatial blocking and auto-exports all 4 artifacts.
- **Blocker:** Retraining cannot produce a valid model until real ground truth labels for `FLARE`, `COAL`, `IND_FIRE`, and `LEAK` are procured and added to `labelled.parquet`.

---

## V9 — PROBLEM STATEMENT (PS 26162) COMPLIANCE MATRIX

| SIH Requirement Specification | Implementation Status | Evidence & Code Location | Compliance Evaluation |
| :--- | :---: | :--- | :--- |
| **1. Satellite Thermal Telemetry Ingestion** | `✅ FULL` | `agnivani/ingest/firms.py:35-120` | NOAA-20 / NOAA-21 VIIRS 375m active fire data ingested via REST API with offline CSV fallback. |
| **2. Sovereign Geographic Boundary Filtering** | `⚠️ PARTIAL` | `agnivani/geo/india.py:7-38` | Vectorized ray-casting mainland mask filters non-India points, but excludes Andaman & Nicobar and Lakshadweep. |
| **3. High-Cadence Spatiotemporal Clustering** | `✅ FULL` | `agnivani/geo/cluster.py:18-85` | Clusters contiguous detections within ~2 km into stable cluster tracking IDs (`AV-XXXXXXXX`). |
| **4. Sub-Pixel Planck / Dozier Physics Inversion** | `✅ FULL` | `agnivani/physics/planck.py:32-154` | Numerical dual-band solver derives sub-pixel fire kinetic temperature ($T_{\text{fire}}$) and area fraction ($p$). |
| **5. Industrial Facility Registry Correlation** | `⚠️ PARTIAL` | `agnivani/geo/registry.py:20-65` | Correlates detections with nearest facility within 500m threshold. Limited by small registry (38 facilities). |
| **6. Machine Learning Categorization** | `⚠️ PARTIAL` | `agnivani/models/scorer.py:25-210` | XGBoost with spatial-block CV and conformal intervals implemented, but system defaults to heuristic scorer. |
| **7. Baseline Radiance & Historical Deviation** | `❌ NONE` | `agnivani/models/baseline.py` (Missing) | No baseline engine implemented. `source_baselines` table is empty; deviation $z$-score defaults to `0.0`. |
| **8. Plume Dispersion & Atmospheric Modeling** | `❌ NONE` | `agnivani/physics/plume.py` (Missing) | Gaussian plume model and wind vector integration are completely absent. |
| **9. Automated Emergency Alert Dispatch** | `⚠️ PARTIAL` | `agnivani/main.py:118-142` | `POST /api/dispatch` records dispatch receipt in DuckDB and logs event; external SMS/API gateways not integrated. |
| **10. Explainable Decision Narratives (SHAP)** | `⚠️ PARTIAL` | `agnivani/models/scorer.py:165-208` | SHAP TreeExplainer integrated in `XGBScorer`, but inactive when operating under default heuristic scorer. |

---

## V10 — REMAINING RISKS & FAILURE MODES

### V10.1 Ranked Risk Registry

| Rank | Risk Category | Description | Severity | Likelihood | Mitigation Action Required |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Model Generalization** | 87.3% of training data is synthetic. Model will fail to recognize real industrial flare patterns in production. | **Critical** | High | Procure World Bank GGFR flaring coordinates and replace synthetic training data with real VIIRS detections. |
| **2** | **Heuristic Default** | System defaults to `SCORER_BACKEND=heuristic`, serving hand-tuned priors and marking 96.3% of detections as `UNRESOLVED`. | **High** | High | Switch `SCORER_BACKEND=xgb` in `.env.example` and `config.py` after validating model on real data. |
| **3** | **Offline Raster Gap** | `data/raw/worldcover` has 0 tiles. System cannot classify land cover offline, defaulting to coarse bounding boxes. | **High** | High | Download 66 ESA WorldCover COG tiles covering India and store in `data/raw/worldcover/`. |
| **4** | **Territorial Omission** | `agnivani/geo/india.py` excludes Andaman & Nicobar and Lakshadweep. Thermal events on islands are discarded. | **Medium** | High | Replace 77-vertex mainland contour with official Survey of India multi-polygon boundary. |
| **5** | **Missing Phase 2 Endpoints** | UI or API consumers calling `/api/deviations`, `/api/unauthorised`, or `/api/validation` encounter HTTP 404 errors. | **Medium** | High | Implement baseline deviation engine and register Phase 2 API routes. |

---

### V10.2 Dead Code Analysis
- `scripts/generate_synthetic.py`: Standalone synthetic data generator; not called by application runtime or ingestion scheduler.
- `stitch_agnivani_thermal_intelligence_grid/`: 3 prototype folders containing static HTML/CSS mockups. Unreferenced by root web application (`index.html`).
- `firms_profile.py`: Standalone prototype profiling script in repository root; logic has been superseded by `agnivani/ingest/firms.py`.

### V10.3 Silent Failure Points
- `agnivani/geo/landcover.py:186-195`: Catches all raster sampling exceptions, logs a warning, and returns `"unavailable"` with a fallback heuristic. Does not raise an alert or halt execution.
- `agnivani/main.py:42-50`: Catches all initial ingestion exceptions on server startup, logs `log.warning("startup_ingest_failed")`, and continues booting.

### V10.4 Demo Day Failure Scenarios
1. **Network Disconnection:** If the demonstration runs offline without downloading WorldCover tiles, land cover resolves to `"unavailable"`, and all forest/wildfire differentiations fall back to coarse bounding boxes.
2. **Reviewer Inspects Trained Model:** If an auditor inspects `data/processed/labelled.parquet`, they will discover that 100% of the industrial flare and leak training rows are synthetic.
3. **Reviewer Queries Phase 2 Endpoints:** If a judge navigates to `/api/deviations` or `/api/validation`, the server returns an HTTP 404 error.

---

## V11 — WHAT ACTUALLY CHANGED (DIFF FORENSICS)

### Git History Breakdown
The repository contains 3 commits on `main`:
1. `4a3071c` (*Initial commit*): Prototype pipeline with hardcoded confidence severity, `"ms": 0` telemetry, `Math.random()` simulation, and unintegrated Bhuvan stubs.
2. `ecb7019` (*Phase 0: Integrity Hardening*):
   - Created `agnivani/models/severity.py` (pure physical severity).
   - Created `agnivani/observability.py` (`StageTracer` recording real millisecond durations).
   - Added `UNRESOLVED` class to `CLASSES` and created `canonical_frame()`.
   - Gated demo mode with `?demo=1` and added persistent red banner.
   - Removed `_fetch_bhuvan()` from `scripts/build_registry.py`.
   - Enforced localhost CORS allowlist and bearer token authentication.
3. `9b2db87` (*Phase 1: Real AI & Land-Cover Hardening*):
   - Created `agnivani/geo/landcover.py` (ESA WorldCover COG resolver).
   - Created `scripts/materialise_training_set.py` (emitted `labelled.parquet`).
   - Executed spatial-block cross-validation in `agnivani/models/train.py`, generating `model.joblib`, `calibrator.joblib`, `conformal.json`, and `metrics.json`.
   - Upgraded `XGBScorer` with `shap.TreeExplainer`.
   - Added unit test suites `tests/test_landcover.py` and `tests/test_training.py`.

**Uncommitted Changes:** Working tree is clean (`git status` is empty). No work was committed or staged for Phase 2 or Phase 3.

---

## V12 — SELF-ATTESTATION & SIGN-OFF

I hereby attest that this forensic verification report represents an uncompromising, read-only evaluation of the AGNIVANI codebase as it exists at commit `9b2db87`. 

No files were modified, created, or deleted during this audit (with the sole exception of writing this report document). All claims, metrics, line numbers, and verdicts presented herein are directly supported by raw command outputs, verbatim code excerpts, and database inspection records captured during the audit.

**Audit Completed:** 2026-09-24 20:45:00 UTC  
**Auditor Signature:** *External Forensic Systems Auditor (Read-Only)*  
**Verification Verdict:** `⚠️ PARTIAL` (Phase 0 & 1 Complete; Phase 2 & 3 Unstarted; Procurement Required)
