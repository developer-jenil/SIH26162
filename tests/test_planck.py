import pytest
from agnivani.physics.planck import planck_radiance,brightness_temp,dozier

def test_planck_roundtrip():
    for wavelength in (3.74,11.45):
        assert brightness_temp(wavelength,planck_radiance(wavelength,1200))==pytest.approx(1200,rel=1e-10)

def test_no_mir_excess():
    r=dozier(300,300,375**2)
    assert not r.converged and r.flags==["NO_MIR_EXCESS"] and r.t_fire_K is None

def test_mixed_pixel_with_tir_as_background_reports_no_root():
    # The specified NRT approximation uses observed I5 as background. For a true
    # mixed pixel that can make the two-band equation unbracketable; report it
    # honestly rather than manufacturing a temperature.
    from agnivani.physics.planck import LAM_MIR,LAM_TIR
    p=.001
    l4=(1-p)*planck_radiance(LAM_MIR,300)+p*planck_radiance(LAM_MIR,1800)
    l5=(1-p)*planck_radiance(LAM_TIR,300)+p*planck_radiance(LAM_TIR,1800)
    r=dozier(brightness_temp(LAM_MIR,l4),brightness_temp(LAM_TIR,l5),375**2)
    assert not r.converged and r.flags==["NO_ROOT"]

def test_single_pixel_with_independent_background():
    from agnivani.physics.planck import LAM_MIR, LAM_TIR
    p = 0.002
    t_true = 1150.0
    t_bg = 290.0
    l4 = (1 - p) * planck_radiance(LAM_MIR, t_bg) + p * planck_radiance(LAM_MIR, t_true)
    l5 = (1 - p) * planck_radiance(LAM_TIR, t_bg) + p * planck_radiance(LAM_TIR, t_true)
    bt_mir = brightness_temp(LAM_MIR, l4)
    bt_tir = brightness_temp(LAM_TIR, l5)
    r = dozier(bt_mir, bt_tir, 375**2, t_bg_K=t_bg)
    assert r.converged is True
    assert r.t_fire_K is not None
    assert 1100.0 <= r.t_fire_K <= 1200.0
    assert 0.0 < r.frac <= 1.0
    assert r.frp_derived_MW is not None and r.frp_derived_MW > 0

def test_self_background_returns_explicit_flag():
    # When t_bg is identical to observed TIR (self-background), do not fabricate a temperature
    r = dozier(330.0, 295.0, 375**2, t_bg_K=295.0)
    assert r.converged is False
    assert r.t_fire_K is None
    assert any(f in r.flags for f in ("NO_ROOT", "BACKGROUND_UNAVAILABLE"))

