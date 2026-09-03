"""Quick smoke-test for the new snapshot endpoint and config shim."""
from fastapi.testclient import TestClient
from agnivani.main import create_app
from agnivani.config import Settings


s = Settings(data_dir="data", offline_mode=True)
app = create_app(s)

with TestClient(app) as c:
    # /api/snapshot
    r = c.get("/api/snapshot")
    print(f"SNAPSHOT status={r.status_code} keys={list(r.json().keys())}")
    snap = r.json()
    print(f"  stats.total_detections={snap['stats']['total_detections']}")
    print(f"  detections count={len(snap['detections'])}")
    print(f"  facilities count={len(snap['facilities'])}")

    # /api/stats
    r2 = c.get("/api/stats")
    print(f"STATS status={r2.status_code} scorer={r2.json()['scorer']}")

    # /api/pipeline/log
    r3 = c.get("/api/pipeline/log")
    print(f"PIPELINE LOG status={r3.status_code} count={len(r3.json())}")

    # / (config shim)
    r4 = c.get("/")
    has_shim = "AGNIVANI_API" in r4.text
    print(f"HTML status={r4.status_code} has_config_shim={has_shim}")
    if has_shim:
        idx = r4.text.find("AGNIVANI_API")
        print(f"  SHIM snippet: ...{r4.text[idx-15:idx+70]}...")

print("\nAll checks passed.")
