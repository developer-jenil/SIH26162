"""Planck radiance and dual-band Dozier sub-pixel retrieval."""
from dataclasses import dataclass, field
import math
import numpy as np
from scipy.optimize import brentq

from typing import NamedTuple

C1 = 1.191042e8
C2 = 1.4387774e4
LAM_MIR = 3.74
LAM_TIR = 11.45
SIGMA = 5.670374419e-8

# Published per-class emission factors:
# - Biomass / Wildfire (WILD): Wooster et al. (2005) (biomass combustion coefficient CF ~ 0.5 kg dry matter / MJ radiant energy);
#   Kaiser et al. (2012) GFAS v1.0; Andreae (2019) / Akagi et al. (2011) emission factors:
#   EF_CO2 ~ 1650 g/kg dry matter -> CO2e ~ 0.5 kg/MJ * 1.65 kg CO2/kg = 0.825 kg CO2e / MJ radiant energy.
#   EF_BC ~ 0.60 g/kg dry matter -> BC ~ 0.5 kg/MJ * 0.60 g/kg = 0.30 g BC / MJ radiant energy.
# - Industrial Fire (IND_FIRE): IPCC (2006) Guidelines for National GHG Inventories, Vol 2 / EPA AP-42 industrial combustion.
#   High soot generation under incomplete industrial combustion: CO2e ~ 0.95 kg/MJ, BC ~ 0.85 g/MJ.
# - Gas Flaring (FLARE): Johnson et al. (2011, 2014) "Measurement of black carbon emissions from flaring";
#   World Bank GGFR; Caulton et al. (2014). Radiative fraction chi_rad ~ 0.18 translates radiant FRP to fuel energy.
#   Unassisted flare soot emission factor ~ 0.65 g BC / MJ radiant energy; CO2e ~ 0.55 kg CO2e / MJ radiant energy.
# - Coal Seam Combustion (COAL): Carras et al. (2009) "Greenhouse gas emissions from spontaneous combustion of coal";
#   Engle et al. (2011). Smoldering coal seam fires produce significant CO2 + CH4 (high CO2e): CO2e ~ 1.10 kg/MJ, BC ~ 0.40 g/MJ.
# - Gas Venting / Leak (LEAK): IPCC AR6 Chapter 5 fugitive methane GWP100 (~29.8) / GWP20 (~82.5).
#   Fugitive unignited hydrocarbon venting: high CO2 equivalent (~1.25 kg CO2e/MJ thermal proxy), zero black carbon (no soot formed).
EMISSION_FACTORS: dict[str, dict[str, float]] = {
    "WILD": {
        "co2e_kg_per_mj": 0.825,
        "bc_g_per_mj": 0.30,
    },
    "IND_FIRE": {
        "co2e_kg_per_mj": 0.950,
        "bc_g_per_mj": 0.85,
    },
    "FLARE": {
        "co2e_kg_per_mj": 0.550,
        "bc_g_per_mj": 0.65,
    },
    "COAL": {
        "co2e_kg_per_mj": 1.100,
        "bc_g_per_mj": 0.40,
    },
    "LEAK": {
        "co2e_kg_per_mj": 1.250,
        "bc_g_per_mj": 0.00,
    },
}


class EmissionProxyResult(NamedTuple):
    co2e_rate_tph: float
    black_carbon_rate_kgph: float


def emission_proxy(cls: str, frp_derived_MW: float | None, span_days: float = 1.0, n_days: int = 1) -> EmissionProxyResult:
    """Estimate emission rates (tonnes CO2e/hour and kg black carbon/hour) from FRP and class.

    1 MW = 1 MJ/s = 3600 MJ/hour.
    co2e_rate_tph = frp_MW * 3600 * co2e_kg_per_mj / 1000 = frp_MW * 3.6 * co2e_kg_per_mj.
    black_carbon_rate_kgph = frp_MW * 3600 * bc_g_per_mj / 1000 = frp_MW * 3.6 * bc_g_per_mj.
    """
    if frp_derived_MW is None or math.isnan(frp_derived_MW) or frp_derived_MW <= 0:
        return EmissionProxyResult(0.0, 0.0)

    factors = EMISSION_FACTORS.get(cls, EMISSION_FACTORS["WILD"])
    co2e_tph = float(frp_derived_MW) * 3.6 * factors["co2e_kg_per_mj"]
    bc_kgph = float(frp_derived_MW) * 3.6 * factors["bc_g_per_mj"]

    return EmissionProxyResult(round(co2e_tph, 4), round(bc_kgph, 4))



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


def dozier(bt_mir_K: float, bt_tir_K: float, pixel_area_m2: float, t_bg_K: float | None = None) -> Retrieval:
    if pixel_area_m2 <= 0:
        raise ValueError("pixel_area_m2 must be positive")
    
    # Priority c / Self-background fallback:
    if t_bg_K is None or float(t_bg_K) >= float(bt_tir_K):
        t_bg = float(bt_tir_K)
        L4 = planck_radiance(LAM_MIR, bt_mir_K)
        B4b = planck_radiance(LAM_MIR, t_bg)
        if L4 <= B4b * 1.0001:
            return Retrieval(None, t_bg, 0.0, None, False, ["NO_MIR_EXCESS"])
        flag = "NO_ROOT" if t_bg_K is None else "BACKGROUND_UNAVAILABLE"
        return Retrieval(None, t_bg, 0.0, None, False, [flag])

    t_bg = float(t_bg_K)
    L4, L5 = planck_radiance(LAM_MIR, bt_mir_K), planck_radiance(LAM_TIR, bt_tir_K)
    B4b, B5b = planck_radiance(LAM_MIR, t_bg), planck_radiance(LAM_TIR, t_bg)
    if L4 <= B4b * 1.0001:
        return Retrieval(None, t_bg, 0.0, None, False, ["NO_MIR_EXCESS"])
    if L5 <= B5b:
        return Retrieval(None, t_bg, 0.0, None, False, ["NO_TIR_EXCESS"])

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

