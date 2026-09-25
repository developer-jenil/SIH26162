"""Smoke-test for the snapshot endpoint, pipeline log, and config shim."""
import urllib.request
import json
from fastapi.testclient import TestClient
from agnivani.main import create_app
from agnivani.config import Settings


def test_live_integration(tmp_path):
    # Try testing running server first if active
    server_online = False
    try:
        req = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)
        if req.status == 200:
            server_online = True
    except Exception:
        server_online = False

    if server_online:
        snap_req = urllib.request.urlopen("http://127.0.0.1:8000/api/snapshot")
        assert snap_req.status == 200
        snap = json.loads(snap_req.read().decode("utf-8"))
        assert "stats" in snap and "detections" in snap and "facilities" in snap

        stats_req = urllib.request.urlopen("http://127.0.0.1:8000/api/stats")
        assert stats_req.status == 200

        log_req = urllib.request.urlopen("http://127.0.0.1:8000/api/pipeline/log")
        assert log_req.status == 200

        root_req = urllib.request.urlopen("http://127.0.0.1:8000/")
        assert root_req.status == 200
        assert "AGNIVANI_API" in root_req.read().decode("utf-8")
    else:
        s = Settings(data_dir=tmp_path, offline_mode=True)
        app = create_app(s)
        with TestClient(app) as c:
            r = c.get("/api/snapshot")
            assert r.status_code == 200
            snap = r.json()
            assert "stats" in snap and "detections" in snap and "facilities" in snap

            r2 = c.get("/api/stats")
            assert r2.status_code == 200

            r3 = c.get("/api/pipeline/log")
            assert r3.status_code == 200

            r4 = c.get("/")
            assert r4.status_code == 200
            assert "AGNIVANI_API" in r4.text
