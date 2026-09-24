"""Tests for DOM contract integrity between HTML and JavaScript."""
import re
from pathlib import Path
import pytest


def test_dom_ids_contract():
    root = Path(__file__).resolve().parent.parent
    index_html = (root / "index.html").read_text(encoding="utf-8")
    app_js = (root / "js" / "app.js").read_text(encoding="utf-8")

    # Find all HTML element IDs defined in index.html
    html_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', index_html))

    # Find all document.getElementById and mustEl lookups in app.js
    js_ids = set(re.findall(r'(?:document\.getElementById|mustEl)\s*\(\s*["\']([^"\']+)["\']\s*\)', app_js))

    # Dynamic IDs constructed with templates (e.g. view-${viewName}) are checked by prefix
    dynamic_prefixes = {"view-"}
    
    missing_ids = []
    for jid in sorted(js_ids):
        if any(jid.startswith(p) for p in dynamic_prefixes):
            continue
        if jid not in html_ids:
            missing_ids.append(jid)

    assert not missing_ids, f"DOM Contract Violation! JavaScript queries IDs missing in index.html: {missing_ids}"


def test_inspection_panel_and_banners_exist():
    root = Path(__file__).resolve().parent.parent
    index_html = (root / "index.html").read_text(encoding="utf-8")
    for req_id in ["inspection-panel", "backend-unreachable-banner", "retry-backend-btn", "demo-mode-persistent-banner"]:
        assert f'id="{req_id}"' in index_html, f"Missing required element #{req_id} in index.html"


def test_quarantined_fixtures():
    import json
    root = Path(__file__).resolve().parent.parent
    fixture_path = root / "js" / "fixtures" / "SIMULATED_demo_detections.json"
    assert fixture_path.exists(), "SIMULATED_demo_detections.json must exist (quarantined)"
    
    # Old un-quarantined file must NOT exist
    assert not (root / "js" / "fixtures" / "demo_detections.json").exists(), "Old demo_detections.json must be renamed"
    
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert len(data) >= 3
    for item in data:
        assert item["id"].startswith("SIM-"), f"Fixture ID {item['id']} must start with SIM-"
        assert item.get("provenance") == "SIMULATED", f"Fixture {item['id']} missing provenance: SIMULATED"
        assert "p" in item and 0.0 < item["p"] <= 1.0, f"Fixture {item['id']} must have valid Dozier p in (0, 1]"
        assert item["severity"] in ["LOW", "HIGH", "CRITICAL"], f"Fixture {item['id']} has invalid severity"

