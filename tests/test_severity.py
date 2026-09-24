from agnivani.models.severity import compute_severity, SEVERITY_LEVELS, BASE_SEVERITY

def test_severity_invariants():
    # 1. A FLARE with frp < 20 and no deviation -> LOW
    sev, rat = compute_severity("FLARE", frp_mw=15.0, deviation_z=None, population_in_radius=None)
    assert sev == "LOW"
    assert "Base hazard for FLARE: LOW" in rat

    # 2. An IND_FIRE with frp >= 50 -> CRITICAL
    sev, rat = compute_severity("IND_FIRE", frp_mw=55.0, deviation_z=None, population_in_radius=None)
    assert sev == "CRITICAL"
    assert "High thermal intensity" in rat

    # 3. A LEAK -> HIGH at minimum, CRITICAL when deviation_z >= 3 or population > 10 000
    sev_base, _ = compute_severity("LEAK", frp_mw=5.0, deviation_z=None, population_in_radius=None)
    assert sev_base == "HIGH"

    sev_dev, rat_dev = compute_severity("LEAK", frp_mw=5.0, deviation_z=3.5, population_in_radius=None)
    assert sev_dev == "CRITICAL"
    assert "Significant baseline departure" in rat_dev

    sev_pop, rat_pop = compute_severity("LEAK", frp_mw=5.0, deviation_z=None, population_in_radius=15000)
    assert sev_pop == "CRITICAL"
    assert "High population exposure" in rat_pop

def test_compute_severity_purity_and_independence_from_confidence():
    # Purity: identical inputs yield identical outputs
    res1 = compute_severity("FLARE", frp_mw=25.0, deviation_z=2.0, population_in_radius=5000)
    res2 = compute_severity("FLARE", frp_mw=25.0, deviation_z=2.0, population_in_radius=5000)
    assert res1 == res2

    # Verify confidence is NOT an accepted parameter in compute_severity
    import inspect
    sig = inspect.signature(compute_severity)
    assert "conf" not in sig.parameters
    assert "confidence" not in sig.parameters

def test_offshore_suppression_severity():
    sev, rat = compute_severity("FLARE", frp_mw=100.0, deviation_z=10.0, offshore_suppressed=True)
    assert sev == "LOW"
    assert "suppressed" in rat.lower()
