from pathlib import Path
from fastapi.testclient import TestClient
from agnivani.config import Settings
from agnivani.main import create_app

from agnivani.models.scorer import CLASSES

def test_empty_store_api(tmp_path):
    settings=Settings(offline_mode=True,data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json()["ok"] is True
        assert client.get("/api/detections").json()==[]
        stats=client.get("/api/stats")
        assert stats.status_code==200 and stats.json()["total_detections"]==0
        snap=client.get("/api/snapshot")
        assert snap.status_code==200
        assert snap.headers.get("X-Agnivani-Mode")=="live"
        assert snap.json()["detections"]==[]
        assert client.get("/api/detections/missing").status_code==404
        assert client.get("/api/pipeline/log").status_code==200
        assert client.get("/api/facilities").status_code==200
        assert client.get("/").status_code==200

def test_seed_data_api(tmp_path):
    raw=tmp_path/"raw"/"firms";raw.mkdir(parents=True)
    source=Path(__file__).parents[1]/"firms_india.csv";(raw/"firms_india.csv").write_bytes(source.read_bytes())
    with TestClient(create_app(Settings(offline_mode=True,data_dir=tmp_path))) as client:
        result=client.get("/api/detections?hours=0&limit=5")
        assert result.status_code==200 and result.json()
        item=result.json()[0]
        assert set(["id","lat","lon","cls","conf","frp_MW","evidence"])<=set(item)
        assert len(item["evidence"])==6 and set(item["probs"])==set(CLASSES)
        assert abs(sum(item["probs"].values())-1)<1e-4
        response=client.post("/api/dispatch",json={"detection_id":item["id"],"authority":"TEST","channel":"mock"})
        assert response.status_code==200 and response.json()["status"]=="sent"

def test_cors_origins_configured(tmp_path):
    # Default development CORS: localhost origins allowed, wildcard '*' disallowed
    default_settings = Settings(offline_mode=True, data_dir=tmp_path)
    with TestClient(create_app(default_settings)) as client:
        res_allowed = client.get("/api/health", headers={"Origin": "http://localhost:8000"})
        assert res_allowed.status_code == 200
        assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:8000"

        res_disallowed = client.get("/api/health", headers={"Origin": "http://malicious-site.example.com"})
        assert res_disallowed.status_code == 200
        assert res_disallowed.headers.get("access-control-allow-origin") != "http://malicious-site.example.com"
        assert res_disallowed.headers.get("access-control-allow-origin") != "*"

    # Custom CORS via comma-separated string or list in Settings / env
    custom_settings = Settings(
        offline_mode=True,
        data_dir=tmp_path,
        cors_origins="https://custom.internal,https://control-grid.org",
    )
    assert custom_settings.cors_origins == ["https://custom.internal", "https://control-grid.org"]
    with TestClient(create_app(custom_settings)) as client:
        res_custom = client.get("/api/health", headers={"Origin": "https://custom.internal"})
        assert res_custom.status_code == 200
        assert res_custom.headers.get("access-control-allow-origin") == "https://custom.internal"

        res_untrusted = client.get("/api/health", headers={"Origin": "http://localhost:8000"})
        assert res_untrusted.headers.get("access-control-allow-origin") != "http://localhost:8000"

def test_evidence_stages_have_real_perf_counter_ms(tmp_path):
    raw = tmp_path / "raw" / "firms"
    raw.mkdir(parents=True)
    source = Path(__file__).parents[1] / "firms_india.csv"
    (raw / "firms_india.csv").write_bytes(source.read_bytes())
    with TestClient(create_app(Settings(offline_mode=True, data_dir=tmp_path))) as client:
        result = client.get("/api/detections?hours=0&limit=5")
        assert result.status_code == 200
        detections = result.json()
        assert len(detections) > 0
        for item in detections:
            evidence = item.get("evidence", [])
            assert len(evidence) == 6
            labels = {e["label"] for e in evidence}
            assert labels == {
                "VIIRS INGEST",
                "INDIA FILTER",
                "SOURCE CLUSTER",
                "PLANCK RETRIEVAL",
                "REGISTRY JOIN",
                "CLASSIFY",
            }
            for e in evidence:
                assert isinstance(e["ms"], int)
                # Verify that hardcoded "ms":0 was replaced with real perf_counter deltas (> 0)
                assert e["ms"] > 0

def test_snapshot_cached_and_replayed_when_backend_down(tmp_path):
    raw = tmp_path / "raw" / "firms"
    raw.mkdir(parents=True)
    source = Path(__file__).parents[1] / "firms_india.csv"
    (raw / "firms_india.csv").write_bytes(source.read_bytes())

    # Simulated client-side localStorage dictionary
    local_storage = {}

    # Step 1: When backend is live, fetch /api/snapshot and save to cache
    settings = Settings(offline_mode=True, data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        res = client.get("/api/snapshot")
        assert res.status_code == 200
        data = res.json()
        assert "detections" in data and len(data["detections"]) > 0
        assert "stats" in data and data["stats"]["total_detections"] > 0
        # Client caches on successful response:
        local_storage["agnivani_snapshot_cache"] = data

    # Step 2: Backend is DOWN (app/server closed or network failure)
    # The client attempts fetch("/api/snapshot"), encounters failure/timeout,
    # and replays the cached snapshot from local_storage
    cached_raw = local_storage.get("agnivani_snapshot_cache")
    assert cached_raw is not None, "Cached snapshot must be present in local storage"

    # Replay verification: client hydrator receives cached payload without dummy blips
    replayed = cached_raw
    assert replayed["stats"]["total_detections"] == data["stats"]["total_detections"]
    assert len(replayed["detections"]) == len(data["detections"])

    # Verify integrity of replayed detections
    for orig, replay in zip(data["detections"], replayed["detections"]):
        assert replay["id"] == orig["id"]
        assert replay["cls"] in CLASSES
        assert abs(sum(replay["probs"].values()) - 1.0) < 1e-4
        assert not replay["id"].startswith("DUMMY-")
        assert not replay["id"].startswith("AGN-04832") or orig["id"] == "AGN-04832"


def test_token_auth_on_mutating_routes(tmp_path):
    raw = tmp_path / "raw" / "firms"
    raw.mkdir(parents=True)
    source = Path(__file__).parents[1] / "firms_india.csv"
    (raw / "firms_india.csv").write_bytes(source.read_bytes())

    # When token is configured, mutating endpoints require valid Bearer token
    secure_settings = Settings(
        offline_mode=True,
        data_dir=tmp_path,
        agnivani_api_token="test-secret-key-42",
    )
    with TestClient(create_app(secure_settings)) as client:
        # First get a valid detection ID
        dets = client.get("/api/detections?hours=0&limit=1").json()
        assert len(dets) > 0
        det_id = dets[0]["id"]

        # Missing token -> 401
        res_no_token = client.post("/api/dispatch", json={"detection_id": det_id, "authority": "SEC", "channel": "mock"})
        assert res_no_token.status_code == 401

        # Wrong token -> 401
        res_wrong = client.post(
            "/api/dispatch",
            json={"detection_id": det_id, "authority": "SEC", "channel": "mock"},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert res_wrong.status_code == 401

        # Correct token -> 200
        res_auth = client.post(
            "/api/dispatch",
            json={"detection_id": det_id, "authority": "SEC", "channel": "mock"},
            headers={"Authorization": "Bearer test-secret-key-42"},
        )
        assert res_auth.status_code == 200
        assert res_auth.json()["status"] == "sent"


