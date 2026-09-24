"""Pipeline runner script for AGNIVANI.

Executes the 6-stage thermal intelligence pipeline and displays measured stage timings.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

def main():
    print("=" * 65)
    print("  AGNIVANI THERMAL PIPELINE INGESTION & ATTRIBUTION RUNNER")
    print("=" * 65)
    url = "http://localhost:8000/api/pipeline/run"
    print(f"Triggering execution against {url}...")
    try:
        t0 = time.perf_counter()
        resp = httpx.post(url, timeout=30.0)
        t_tot = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200:
            data = resp.json()
            print("\n[SUCCESS] Pipeline executed cleanly:")
            print(f"  Execution ID    : {data.get('run_id')}")
            print(f"  Raw Detections  : {data.get('num_raw')}")
            print(f"  Sources Clustered: {data.get('num_sources')}")
            print(f"  Total Duration  : {data.get('total_ms', t_tot):.2f} ms\n")
            print("  Stage Measured Timings:")
            for stage, ms in data.get("stages", {}).items():
                print(f"    - {stage:<20}: {ms:6.2f} ms")
            return 0
        else:
            print(f"[FAIL] Server responded with HTTP {resp.status_code}: {resp.text}")
            return 1
    except httpx.ConnectError:
        print("[WARN] Local server at http://localhost:8000 is not running.")
        print("Executing in-process standalone pipeline run...")
        from agnivani.config import Settings
        from agnivani.main import create_app
        from starlette.testclient import TestClient
        settings = Settings(data_dir=ROOT / "data", offline_mode=True)
        app = create_app(settings)
        with TestClient(app) as client:
            resp = client.post("/api/pipeline/run")
            if resp.status_code == 200:
                data = resp.json()
                print("\n[SUCCESS] In-process pipeline run complete:")
                print(f"  Raw Detections  : {data.get('num_raw')}")
                print(f"  Sources Clustered: {data.get('num_sources')}")
                print(f"  Total Duration  : {data.get('total_ms'):.2f} ms\n")
                print("  Stage Measured Timings:")
                for stage, ms in data.get("stages", {}).items():
                    print(f"    - {stage:<20}: {ms:6.2f} ms")
                return 0
            else:
                print(f"[FAIL] In-process pipeline failed: {resp.text}")
                return 1

if __name__ == "__main__":
    sys.exit(main())
