"""Unit tests for POST /api/pipeline/run and GET /api/pipeline/runs."""
import io
import pytest
from starlette.testclient import TestClient
from agnivani.config import Settings
from agnivani.main import create_app


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path, offline_mode=True)
    # copy corridor files into tmp_path
    import shutil
    raw_dir = tmp_path / "raw" / "firms"
    raw_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy("data/raw/firms/gujarat_noaa20.csv", raw_dir / "gujarat_noaa20.csv")
    shutil.copy("data/raw/firms/gujarat_noaa21.csv", raw_dir / "gujarat_noaa21.csv")
    shutil.copy("data/raw/firms/gujarat_snpp.csv", raw_dir / "gujarat_snpp.csv")
    
    app = create_app(settings)
    with TestClient(app) as tc:
        yield tc


def test_get_pipeline_runs(client):
    res = client.get("/api/pipeline/runs")
    assert res.status_code == 200
    runs = res.json()
    assert isinstance(runs, list)


def test_post_pipeline_run_corridor(client):
    res = client.post("/api/pipeline/run")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["num_raw"] == 170
    assert data["num_sources"] == 41
    assert data["total_ms"] > 0
    stages = data["stages"]
    for expected_stage in ["VIIRS INGEST", "INDIA FILTER", "SOURCE CLUSTER", "PLANCK RETRIEVAL", "REGISTRY JOIN", "CLASSIFY"]:
        assert expected_stage in stages
        assert stages[expected_stage] >= 0

    # Ensure it is now recorded in /api/pipeline/runs
    history_res = client.get("/api/pipeline/runs")
    assert history_res.status_code == 200
    history = history_res.json()
    assert any(h["run_id"] == data["run_id"] for h in history)


def test_post_pipeline_run_invalid_extension(client):
    file_bytes = b"something"
    res = client.post(
        "/api/pipeline/run",
        files={"file": ("invalid.txt", io.BytesIO(file_bytes), "text/plain")}
    )
    assert res.status_code == 422
    assert "Only CSV files are supported" in res.json()["detail"]


def test_post_pipeline_run_missing_columns(client):
    file_bytes = b"col1,col2\n1,2\n"
    res = client.post(
        "/api/pipeline/run",
        files={"file": ("firms.csv", io.BytesIO(file_bytes), "text/csv")}
    )
    assert res.status_code == 422
    assert "missing required columns" in res.json()["detail"].lower()
