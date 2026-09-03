"""Planck radiance and dual-band Dozier sub-pixel retrieval."""
from dataclasses import dataclass, field
import math
import numpy as np
from scipy.optimize import brentq

C1 = 1.191042e8
C2 = 1.4387774e4
LAM_MIR = 3.74
LAM_TIR = 11.45
SIGMA = 5.670374419e-8


def planck_radiance(lam_um: float, T_K: float) -> float:
    if lam_um <= 0 or T_K <= 0:
        raise ValueError("wavelength and temperature must be positive")
    exponent = float(np.clip(C2 / (lam_um * T_K), -700.0, 700.0))
    return C1 / (lam_um ** 5 * math.expm1(exponent))


def brightness_temp(lam_um: float, radiance: float) -> float:
    if lam_um <= 0 or radiance <= 0:
        raise ValueError("wavelength and radiance must be positive")
    return C2 / (lam_um * math.log1p(C1 / (lam_um ** 5 * radiance)))


@dataclass
class Retrieval:
    t_fire_K: float | None
    t_bg_K: float
    frac: float
    frp_derived_MW: float | None
    converged: bool
    flags: list[str] = field(default_factory=list)


def dozier(bt_mir_K: float, bt_tir_K: float, pixel_area_m2: float) -> Retrieval:
    if pixel_area_m2 <= 0:
        raise ValueError("pixel_area_m2 must be positive")
    L4, L5 = planck_radiance(LAM_MIR, bt_mir_K), planck_radiance(LAM_TIR, bt_tir_K)
    t_bg = float(bt_tir_K)
    B4b, B5b = planck_radiance(LAM_MIR, t_bg), planck_radiance(LAM_TIR, t_bg)
    if L4 <= B4b * 1.0001:
        return Retrieval(None, t_bg, 0.0, None, False, ["NO_MIR_EXCESS"])

    def g(temp: float) -> float:
        return (L4 - B4b) * (planck_radiance(LAM_TIR, temp) - B5b) - (L5 - B5b) * (planck_radiance(LAM_MIR, temp) - B4b)

    grid = np.arange(t_bg + 0.5, 3000.01, 0.5)
    previous_t, previous_g = float(grid[0]), g(float(grid[0]))
    root = None
    for current_t in grid[1:]:
        current_t, current_g = float(current_t), g(float(current_t))
        if previous_g == 0 or previous_g * current_g < 0:
            root = previous_t if previous_g == 0 else brentq(g, previous_t, current_t, xtol=1e-3)
            break
        previous_t, previous_g = current_t, current_g
    if root is None:
        return Retrieval(None, t_bg, 0.0, None, False, ["NO_ROOT"])

    raw_frac = (L4 - B4b) / (planck_radiance(LAM_MIR, root) - B4b)
    frac = min(1.0, max(float(np.finfo(float).eps), raw_frac))
    flags = ["P_CLIPPED"] if frac != raw_frac else []
    frp = frac * pixel_area_m2 * SIGMA * root ** 4 / 1e6
    return Retrieval(float(root), t_bg, frac, float(frp), True, flags)
