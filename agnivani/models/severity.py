"""Physics-based and deviation-based severity classification for thermal anomalies."""
from __future__ import annotations

SEVERITY_LEVELS: list[str] = ["LOW", "MODERATE", "HIGH", "CRITICAL"]

# Base hazard index mapping into SEVERITY_LEVELS (0: LOW, 1: MODERATE, 2: HIGH, 3: CRITICAL)
BASE_SEVERITY: dict[str, int] = {
    "LEAK": 2,           # Base HIGH; escalates to CRITICAL on baseline deviation or population exposure
    "IND_FIRE": 2,       # Base HIGH; escalates to CRITICAL on high FRP or severe deviation
    "COAL": 2,           # Base HIGH (persistent subsurface combustion)
    "WILD": 2,           # Base HIGH
    "GEO": 1,            # Base MODERATE
    "UNAUTHORISED": 1,   # Base MODERATE
    "FLARE": 0,          # Base LOW (routine operational flaring)
    "UNRESOLVED": 1,     # Base MODERATE (never default to most alarming class)
}


def compute_severity(
    cls: str,
    frp_mw: float | None,
    deviation_z: float | None = None,
    population_in_radius: int | None = None,
    offshore_suppressed: bool = False,
) -> tuple[str, str]:
    """Return (severity, rationale).

    Severity is a function of hazard class, radiative power, deviation from the
    source's own baseline, and population exposure — NEVER of classifier confidence.
    `deviation_z` and `population_in_radius` are optional and default to neutral.
    """
    if offshore_suppressed:
        return "LOW", "Offshore marine thermal cluster suppressed from terrestrial alerting"

    base_score = BASE_SEVERITY.get(cls, 1)
    score = base_score
    reasons: list[str] = [f"Base hazard for {cls}: {SEVERITY_LEVELS[base_score]}"]

    # Radiative power adjustments
    frp = frp_mw if (frp_mw is not None and frp_mw >= 0) else 0.0
    if frp >= 50.0:
        score += 2
        reasons.append(f"High thermal intensity (FRP {frp:.1f} MW >= 50 MW: +2)")
    elif frp >= 20.0:
        score += 1
        reasons.append(f"Elevated thermal intensity (FRP {frp:.1f} MW >= 20 MW: +1)")

    # Baseline deviation adjustments
    if deviation_z is not None:
        if deviation_z >= 5.0:
            score += 2
            reasons.append(f"Severe baseline departure (z={deviation_z:.1f} >= 5.0: +2)")
        elif deviation_z >= 3.0:
            score += 1
            reasons.append(f"Significant baseline departure (z={deviation_z:.1f} >= 3.0: +1)")

    # Population exposure adjustments
    if population_in_radius is not None and population_in_radius > 10_000:
        score += 1
        reasons.append(f"High population exposure ({population_in_radius:,} persons in impact radius: +1)")

    clamped_score = max(0, min(3, score))
    final_severity = SEVERITY_LEVELS[clamped_score]
    rationale = "; ".join(reasons)
    return final_severity, rationale
