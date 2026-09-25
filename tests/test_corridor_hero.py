"""Tests for Gujarat corridor bounds, real hero detections, provenance and preflight endpoints."""
import pytest
from starlette.testclient import TestClient
from agnivani.config import Settings
from agnivani.main import create_app


@pytest.fixture
def client():
    import urllib.request
    import json
    server_online = False
    try:
        req = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)
        if req.status == 200:
            server_online = True
    except Exception:
        server_online = False

    if server_online:
        class LiveClientWrapper:
            def get(self, url, **kwargs):
                full_url = f"http://127.0.0.1:8000{url}"
                try:
                    req = urllib.request.urlopen(full_url)
                    data = req.read().decode("utf-8")
                    class Resp:
                        status_code = req.status
                        def json(self):
                            return json.loads(data)
                        @property
                        def text(self):
                            return data
                    return Resp()
                except urllib.error.HTTPError as e:
                    class Resp:
                        status_code = e.code
                        def json(self):
                            return json.loads(e.read().decode("utf-8"))
                        @property
                        def text(self):
                            return str(e)
                    return Resp()
        yield LiveClientWrapper()
    else:
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
    assert "2026-09-20 to 2026-09-24" in data["temporal_window"]
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


def test_facility_view_match_count_matches_provenance(client):
    """Verify that facility matches endpoint matches /api/provenance detections_matched for FAC-004."""
    prov_res = client.get("/api/provenance")
    assert prov_res.status_code == 200
    prov_data = prov_res.json()
    expected_matches = prov_data.get("detections_matched", 4)
    assert expected_matches == 4, f"Expected 4 detections_matched in provenance, got {expected_matches}"

    fac_res = client.get("/api/facilities/FAC-004/matches")
    assert fac_res.status_code == 200
    fac_matches = fac_res.json()
    assert len(fac_matches) == expected_matches == 4, (
        f"Facility view match count ({len(fac_matches)}) must equal provenance detections_matched ({expected_matches})"
    )

    match_ids = {d["id"] for d in fac_matches}
    assert "AV-0B12A4B9" in match_ids
    assert "AV-95BA9779" in match_ids
    assert "AV-07D8247D" in match_ids
    assert "AV-EF7A2C35" in match_ids

    for d in fac_matches:
        assert d["id"] is not None
        assert d["cls"] in ("FLARE", "LEAK")
        assert d.get("dist_facility_m") is not None and d["dist_facility_m"] <= 3500.0
        assert d.get("conf") is not None and 0.0 < d["conf"] <= 1.0
        if d["cls"] == "FLARE":
            assert d.get("temp_K") is not None and 350.0 <= d["temp_K"] <= 800.0
            assert d.get("frp_MW") is not None and d["frp_MW"] > 0.0


def test_dossier_severity_badge_matches_compute_severity_for_every_hero(client):
    """Verify compute_severity returns LOW for FLARE below 80 MW,
    and hero stored severity / frontend badge matches compute_severity(cls, frp)."""
    from agnivani.models.severity import compute_severity
    from pathlib import Path
    import re

    sev_hero1, r1 = compute_severity(cls="FLARE", frp_mw=9.23)
    assert sev_hero1 == "LOW", f"Expected LOW for routine flare at 9.23 MW, got {sev_hero1} ({r1})"

    sev_hero2, r2 = compute_severity(cls="FLARE", frp_mw=10.37)
    assert sev_hero2 == "LOW", f"Expected LOW for routine flare at 10.37 MW, got {sev_hero2} ({r2})"

    res = client.get("/api/detections?hours=0&limit=100")
    assert res.status_code == 200
    detections = {d["id"]: d for d in res.json()}

    h1 = detections["AV-0B12A4B9"]
    h1_computed_sev, _ = compute_severity(cls=h1["cls"], frp_mw=h1.get("frp_MW"))
    assert h1_computed_sev == "LOW"
    assert h1["severity"] == h1_computed_sev == "LOW", f"AV-0B12A4B9 stored severity must be LOW, got {h1['severity']}"

    h2 = detections["AV-95BA9779"]
    h2_computed_sev, _ = compute_severity(cls=h2["cls"], frp_mw=h2.get("frp_MW"))
    assert h2_computed_sev == "LOW"
    assert h2["severity"] == h2_computed_sev == "LOW", f"AV-95BA9779 stored severity must be LOW, got {h2['severity']}"

    root = Path(__file__).resolve().parent.parent
    index_html = (root / "index.html").read_text(encoding="utf-8")
    assert re.search(r'id=["\']dossier-severity["\'][\s\S]*?LOW[\s\S]*?</h1>', index_html), (
        "Dossier badge for AV-0B12A4B9 must read LOW on screen in index.html"
    )
    assert not re.search(r'id=["\']dossier-severity["\'][\s\S]*?HIGH[\s\S]*?</h1>', index_html), (
        "Dossier badge must not read HIGH for AV-0B12A4B9 in index.html"
    )

    app_js = (root / "js" / "app.js").read_text(encoding="utf-8")
    assert "id: 'AV-0B12A4B9'" in app_js
    assert "severity: 'LOW'" in app_js


def test_analytics_observation_footprint_centre_in_bbox():
    """Verify that Analytics Corridor basemap center lies inside the real Gujarat detection bbox (21.099–23.408 N, 69.696–73.121 E)."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    index_html = (root / "index.html").read_text(encoding="utf-8")
    app_js = (root / "js" / "app.js").read_text(encoding="utf-8")

    bbox_min_lat = 21.099
    bbox_max_lat = 23.408
    bbox_min_lon = 69.696
    bbox_max_lon = 73.121

    center_match = re.search(r'id=["\']analytics-map-container["\'][^>]*data-initial-center=["\']\[([^,]+),\s*([^\]]+)\]["\']', index_html)
    assert center_match, "analytics-map-container must define data-initial-center in index.html"
    html_lat = float(center_match.group(1))
    html_lon = float(center_match.group(2))

    assert bbox_min_lat <= html_lat <= bbox_max_lat, f"HTML center lat {html_lat} outside bbox [{bbox_min_lat}, {bbox_max_lat}]"
    assert bbox_min_lon <= html_lon <= bbox_max_lon, f"HTML center lon {html_lon} outside bbox [{bbox_min_lon}, {bbox_max_lon}]"

    js_center_match = re.search(r'ANALYTICS_CORRIDOR_CENTER\s*=\s*\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]', app_js)
    assert js_center_match, "ANALYTICS_CORRIDOR_CENTER must be defined in js/app.js"
    js_lat = float(js_center_match.group(1))
    js_lon = float(js_center_match.group(2))

    assert bbox_min_lat <= js_lat <= bbox_max_lat, f"JS center lat {js_lat} outside bbox [{bbox_min_lat}, {bbox_max_lat}]"
    assert bbox_min_lon <= js_lon <= bbox_max_lon, f"JS center lon {js_lon} outside bbox [{bbox_min_lon}, {bbox_max_lon}]"

    for prohibited in ["Haladgaon", "Samudrapur", "Pothra", "20.76"]:
        assert prohibited.lower() not in index_html.lower(), f"Prohibited Maharashtra reference '{prohibited}' found in index.html"
        assert prohibited.lower() not in app_js.lower(), f"Prohibited Maharashtra reference '{prohibited}' found in js/app.js"

