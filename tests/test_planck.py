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
