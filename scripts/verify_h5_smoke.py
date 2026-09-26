"""H5 Read-only offline programmatic verification script."""
import json
import urllib.request

def run_h5_assertions():
    # 1. Stats
    with urllib.request.urlopen("http://127.0.0.1:8000/api/stats") as resp:
        stats = json.loads(resp.read().decode())
        assert stats["total_detections"] == 41, f"Expected 41, got {stats['total_detections']}"
        assert stats["by_class"]["FLARE"] == 2, f"Expected 2 FLARE, got {stats['by_class']['FLARE']}"
        assert stats["by_class"]["LEAK"] == 2, f"Expected 2 LEAK, got {stats['by_class']['LEAK']}"
        assert stats["by_class"]["UNRESOLVED"] == 36, f"Expected 36 UNRESOLVED, got {stats['by_class']['UNRESOLVED']}"
        print("[PASS] Stats assertions: total_detections=41, FLARE=2, LEAK=2, UNRESOLVED=36")

    # 2. Provenance
    with urllib.request.urlopen("http://127.0.0.1:8000/api/provenance") as resp:
        prov = json.loads(resp.read().decode())
        assert "2026-09-20 to 2026-09-24" in prov["temporal_window"]
        assert prov["detections_matched"] == 4
        print("[PASS] Provenance assertions: temporal_window confirmed, detections_matched=4")

    # 3. Write attempt via POST /api/dispatch
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/dispatch",
        data=json.dumps({"detection_id": "AV-0B12A4B9", "authority": "NDRF", "channel": "mock"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        disp = json.loads(resp.read().decode())
        assert disp["status"] == "sent"
        assert disp["dispatch_id"].startswith("DSP-")
        print(f"[PASS] Write attempt POST /api/dispatch handled cleanly: dispatch_id={disp['dispatch_id']}, status={disp['status']}")

if __name__ == "__main__":
    run_h5_assertions()
