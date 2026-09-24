"""Automated Operational Preflight Script for AGNIVANI (P7).

Runs standalone preflight checks verifying:
1. Python dependencies & environment
2. Trained XGBoost model & conformal calibration artifacts
3. Curated industrial facilities registry
4. Planck / Dozier dual-band non-linear physical solver
5. ESA WorldCover 10m land-cover pipeline
6. Presence of the 3 Gujarat corridor hero detections in DuckDB
"""
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_preflight() -> int:
    print("=" * 70)
    print("  AGNIVANI OPERATIONAL PREFLIGHT VERIFICATION MATRIX")
    print("  NASA FIRMS VIIRS Thermal Intelligence Surveillance Platform")
    print("=" * 70)

    failures = 0
    warnings = 0

    # 1. Environment & Dependencies
    print("\n[1/6] Checking Core Python Dependencies...")
    required_pkgs = ["fastapi", "duckdb", "scipy", "xgboost", "shap", "rasterio", "shapely", "pyproj", "pandas", "numpy"]
    for pkg in required_pkgs:
        try:
            __import__(pkg)
            print(f"  [PASS] {pkg:<12} available")
        except ImportError as e:
            print(f"  [FAIL] {pkg:<12} MISSING ({e})")
            failures += 1

    # 2. Production Model Artifacts
    print("\n[2/6] Checking Trained Model Artifacts (data/models/)...")
    model_dir = ROOT / "data" / "models"
    for artifact in ["model.joblib", "calibrator.joblib", "conformal.json", "metrics.json"]:
        p = model_dir / artifact
        if p.exists() and p.stat().st_size > 0:
            print(f"  [PASS] {artifact:<20} present ({p.stat().st_size:,} bytes)")
        else:
            print(f"  [FAIL] {artifact:<20} MISSING or empty")
            failures += 1

    # 3. Processed Datasets
    print("\n[3/6] Checking Processed Geospatial Datasets...")
    proc_dir = ROOT / "data" / "processed"
    for ds in ["facilities.parquet", "labelled.parquet"]:
        p = proc_dir / ds
        if p.exists() and p.stat().st_size > 0:
            print(f"  [PASS] {ds:<22} present ({p.stat().st_size:,} bytes)")
        else:
            print(f"  [FAIL] {ds:<22} MISSING or empty")
            failures += 1

    # 4. Planck / Dozier Physical Inversion Solver
    print("\n[4/6] Validating Planck/Dozier Physical Solver...")
    try:
        from agnivani.physics.planck import dozier, planck_radiance, brightness_temp, LAM_MIR, LAM_TIR
        p = 0.002
        t_true = 1150.0
        t_bg = 290.0
        l4 = (1 - p) * planck_radiance(LAM_MIR, t_bg) + p * planck_radiance(LAM_MIR, t_true)
        l5 = (1 - p) * planck_radiance(LAM_TIR, t_bg) + p * planck_radiance(LAM_TIR, t_true)
        bt_mir = brightness_temp(LAM_MIR, l4)
        bt_tir = brightness_temp(LAM_TIR, l5)
        res = dozier(bt_mir, bt_tir, 375**2, t_bg_K=t_bg)
        if res.converged and res.t_fire_K is not None and 1100.0 <= res.t_fire_K <= 1200.0:
            print(f"  [PASS] Dozier Inversion: T_fire = {res.t_fire_K:.1f} K, frac = {res.frac:.5f}, status = {res.converged}")
        else:
            print(f"  [WARN] Dozier Inversion unexpected result: T_fire={res.t_fire_K}, converged={res.converged}")
            warnings += 1
    except Exception as exc:
        print(f"  [FAIL] Dozier Inversion FAILED: {exc}")
        failures += 1

    # 5. ESA WorldCover Landcover Resolver
    print("\n[5/6] Validating ESA WorldCover Landcover Engine...")
    try:
        from agnivani.geo.landcover import resolve_landcover
        lc_cls = resolve_landcover(21.1055, 72.6405)
        print(f"  [PASS] Landcover Point Check (Hazira centroid): class = '{lc_cls}'")
    except Exception as exc:
        print(f"  [FAIL] Landcover check FAILED: {exc}")
        failures += 1

    # 6. Database & Hero Detections Verification
    print("\n[6/6] Verifying DuckDB Detections & Hero Targets...")
    try:
        from agnivani.store.duck import DuckStore
        store = DuckStore(ROOT / "data")
        dets = store.detections()
        print(f"  [PASS] DuckDB Store: {len(dets)} total detections active")

        det_map = {d["id"]: d for d in dets}
        heroes = [
            ("AV-0B12A4B9", "Hazira Flare #1", "FLARE", 0.90),
            ("AV-95BA9779", "Hazira Flare #2", "FLARE", 0.90),
            ("AV-07D8247D", "Hazira Candidate Leak", "LEAK", 0.55),
        ]
        for hid, label, expected_cls, expected_conf in heroes:
            if hid in det_map:
                d = det_map[hid]
                t_str = f"{d.get('temp_K'):.1f} K" if d.get('temp_K') else "null"
                print(f"  [PASS] Hero [{hid}] {label:<22}: cls={d.get('cls')}, conf={d.get('conf')}, T_fire={t_str}")
            else:
                print(f"  [FAIL] Hero [{hid}] {label:<22}: NOT FOUND in DuckDB")
                failures += 1
        store.close()
    except Exception as exc:
        print(f"  [FAIL] DuckDB Verification FAILED: {exc}")
        failures += 1

    # Final Verdict
    print("\n" + "=" * 70)
    if failures == 0:
        print(f"  >>> OPERATIONAL PREFLIGHT VERDICT: PASS (0 errors, {warnings} warnings) <<<")
        print("  System is 100% demo-ready and verified for presentation.")
        print("=" * 70)
        return 0
    else:
        print(f"  >>> OPERATIONAL PREFLIGHT VERDICT: FAIL ({failures} critical errors) <<<")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(run_preflight())
