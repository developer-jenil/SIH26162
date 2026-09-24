"""Tests for Gujarat corridor bounds, real hero detections, provenance and preflight endpoints."""
import pytest
from starlette.testclient import TestClient
from agnivani.config import Settings
from agnivani.main import create_app


@pytest.fixture
def client():
    settings = Settings(offline_mode=True)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def test_corridor_heroes_exist_in_detections(client):
    """Verify that the 3 demo hero detections exist in the live database with exact physics."""
    res = client.get("/api/detections?hours=0&limit=100")
    assert res.status_code == 200
    detections = res.json()
    assert len(detections) >= 40

    det_map = {d["id"]: d for d in detections}

    # Hero 1: AV-0B12A4B9
    assert "AV-0B12A4B9" in det_map, "Hero 1 AV-0B12A4B9 must exist"
    h1 = det_map["AV-0B12A4B9"]
    assert h1["cls"] == "FLARE"
    assert h1["facility_name"] == "Hazira LNG/Steel"
    assert h1["temp_K"] is not None
    assert 450.0 <= h1["temp_K"] <= 550.0, f"Expected T_fire ~486K, got {h1['temp_K']}"
    assert h1["frp_MW"] is not None and h1["frp_MW"] > 5.0
    assert h1["conf"] >= 0.80

    # Hero 2: AV-95BA9779
    assert "AV-95BA9779" in det_map, "Hero 2 AV-95BA9779 must exist"
    h2 = det_map["AV-95BA9779"]
    assert h2["cls"] == "FLARE"
    assert h2["facility_name"] == "Hazira LNG/Steel"
    assert h2["temp_K"] is not None
    assert 450.0 <= h2["temp_K"] <= 550.0, f"Expected T_fire ~506K, got {h2['temp_K']}"
    assert h2["frp_MW"] is not None and h2["frp_MW"] > 5.0
    assert h2["conf"] >= 0.80

    # Hero 3: AV-07D8247D (Candidate Leak - Condition C3)
    assert "AV-07D8247D" in det_map, "Hero 3 AV-07D8247D must exist"
    h3 = det_map["AV-07D8247D"]
    assert h3["cls"] == "LEAK"
    assert h3["conf"] == 0.55, f"Candidate leak confidence must be exactly 0.55, got {h3['conf']}"
    assert h3["temp_K"] is None, "Candidate leak must have null T_fire"
    assert "candidate fugitive thermal anomaly - low confidence" in h3["reason"]


def test_provenance_endpoint(client):
    """Verify GET /api/provenance disclosure and integrity contract (P5, C2, C3, C4)."""
    res = client.get("/api/provenance")
    assert res.status_code == 200
    data = res.json()

    assert data["dataset_name"] == "Gujarat Industrial Corridor (VIIRS 5-Day NRT)"
    assert data["sensor"] == "VIIRS NOAA-20 / NOAA-21 (375m)"
    assert data["total_detections"] >= 40
    assert data["facilities_matched"] >= 1
    assert data["detections_matched"] >= 4

    # Condition C2 disclosure
    assert "empirically derived from a 5-day corridor sample (n=29); to be re-derived as more data arrives." in data["threshold_disclosure"]

    # Condition C3 disclosure
    assert "candidate fugitive thermal anomalies" in data["candidate_leak_disclosure"]
    assert "0.55" in data["candidate_leak_disclosure"]

    # Condition C4 disclosure
    assert data["unresolved_count"] >= 30
    assert "non-industrial thermal activity in window - deliberately unattributed" in data["unresolved_label"]

    # Heroes list
    heroes = {h["id"]: h for h in data["heroes"]}
    assert "AV-0B12A4B9" in heroes
    assert "AV-95BA9779" in heroes
    assert "AV-07D8247D" in heroes


def test_preflight_endpoint(client):
    """Verify GET /api/preflight automated operational verification (P7)."""
    res = client.get("/api/preflight")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] in ("PASS", "WARN")
    check_names = {c["name"]: c for c in data["checks"]}

    assert "DuckDB Store" in check_names
    assert check_names["DuckDB Store"]["status"] == "PASS"

    assert "Facilities Registry" in check_names
    assert check_names["Facilities Registry"]["status"] == "PASS"

    assert "Classification Scorer" in check_names
    assert check_names["Classification Scorer"]["status"] == "PASS"

    assert "Planck/Dozier Physical Inversion" in check_names
    assert check_names["Planck/Dozier Physical Inversion"]["status"] == "PASS"

    assert "ESA WorldCover Landcover" in check_names
    assert check_names["ESA WorldCover Landcover"]["status"] == "PASS"

    assert "Hero Detections Verification" in check_names
    assert check_names["Hero Detections Verification"]["status"] == "PASS"
