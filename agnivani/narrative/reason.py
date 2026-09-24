"""Narrative reason generator and regulatory compliance citation engine.

Builds an evidence-grounded narrative explanation for thermal anomalies,
citing relevant statutory standards (CPCB, NDMA, DGMS, PNGRB) and suggesting actions.
Guards strictly against numeric hallucinations by validating that every numeric token
in the narrative exists within the input evidence dictionary.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Literal
import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()

# Standard statutory tags and regulatory descriptions
STATUTORY_RULES: dict[str, tuple[str, str, str]] = {
    "FLARE": (
        "CPCB-FLARE-PERMIT",
        "CPCB flare-permit standard",
        "audit plant operational logs and inspect flare combustion efficiency",
    ),
    "IND_FIRE": (
        "NDMA-INDUSTRIAL-SAFETY",
        "NDMA industrial-safety guidelines",
        "dispatch emergency industrial firefighting unit and verify perimeter containment",
    ),
    "COAL": (
        "DGMS-COAL-FIRE",
        "DGMS coal-fire guidelines",
        "execute thermal imaging survey and initiate nitrogen foam suppression",
    ),
    "WILD": (
        "CPCB-AGRICULTURAL-BURN",
        "CPCB agricultural-burn regulation",
        "notify state pollution control board and mobilize local fire containment",
    ),
    "LEAK": (
        "PNGRB-GAS-LEAK",
        "PNGRB gas-leak standard",
        "deploy optical gas imaging survey to isolate fugitive emissions",
    ),
    "OFFSHORE_SUPPRESSED": (
        "OFFSHORE-SUPPRESSED",
        "offshore marine observation protocol",
        "monitor subsequent orbital passes without ground dispatch",
    ),
}


def build_evidence(
    cls: str,
    conf: float,
    lo: float,
    hi: float,
    facility_name: str | None = None,
    facility_sector: str | None = None,
    dist_facility_m: float | None = None,
    t_fire_K: float | None = None,
    frp_max: float = 0.0,
    n_days: int = 1,
    night_frac: float = 0.0,
    diurnal_shape: str | None = None,
    landcover_class: str | None = None,
    co2e_rate_tph: float | None = None,
    offshore_suppressed: bool = False,
) -> dict[str, Any]:
    """Build a compact evidence dictionary per alert from REAL fields only."""
    return {
        "cls": str(cls),
        "conf": round(float(conf), 4),
        "lo": round(float(lo), 4),
        "hi": round(float(hi), 4),
        "facility_name": str(facility_name) if (facility_name and pd.notna(facility_name)) else None,
        "facility_sector": str(facility_sector) if (facility_sector and pd.notna(facility_sector)) else None,
        "dist_facility_m": round(float(dist_facility_m), 1) if (dist_facility_m is not None and pd.notna(dist_facility_m) and np.isfinite(dist_facility_m)) else None,
        "t_fire_K": round(float(t_fire_K), 1) if (t_fire_K is not None and pd.notna(t_fire_K) and np.isfinite(t_fire_K)) else None,
        "frp_max": round(float(frp_max), 2) if (frp_max is not None and pd.notna(frp_max)) else 0.0,
        "n_days": int(n_days) if (n_days is not None and pd.notna(n_days)) else 1,
        "night_frac": round(float(night_frac), 4) if (night_frac is not None and pd.notna(night_frac)) else 0.0,
        "diurnal_shape": str(diurnal_shape) if (diurnal_shape and pd.notna(diurnal_shape)) else None,
        "landcover_class": str(landcover_class) if (landcover_class and pd.notna(landcover_class)) else None,
        "co2e_rate_tph": round(float(co2e_rate_tph), 4) if (co2e_rate_tph is not None and pd.notna(co2e_rate_tph)) else None,
        "offshore_suppressed": bool(offshore_suppressed),
    }


def extract_allowed_numbers(evidence: dict[str, Any]) -> set[float]:
    """Collect all valid numeric representations grounded in the evidence dictionary."""
    allowed = {0.0, 1.0}
    for k, v in evidence.items():
        if v is None:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            try:
                val = float(v)
            except (ValueError, TypeError):
                continue
            if not np.isfinite(val):
                continue
            allowed.add(round(val, 4))
            allowed.add(round(val, 3))
            allowed.add(round(val, 2))
            allowed.add(round(val, 1))
            allowed.add(float(int(round(val))))

            # Percentage representations (e.g. 0.85 -> 85, 85%)
            if 0.0 <= val <= 1.0:
                allowed.add(round(val * 100.0, 2))
                allowed.add(round(val * 100.0, 1))
                allowed.add(float(int(round(val * 100.0))))

            # Kilometer representation for meter distances
            if k == "dist_facility_m" and val > 0:
                km = val / 1000.0
                allowed.add(round(km, 3))
                allowed.add(round(km, 2))
                allowed.add(round(km, 1))
                allowed.add(float(int(round(km))))

            # Celsius representation for Kelvin temperatures
            if k == "t_fire_K" and val > 100:
                celsius = val - 273.15
                allowed.add(round(celsius, 1))
                allowed.add(float(int(round(celsius))))

    return allowed


def validate_no_hallucinated_numbers(text: str, evidence: dict[str, Any]) -> bool:
    """Anti-hallucination guard: asserts that every numeric token in text exists in evidence."""
    if not text:
        return False
    allowed = extract_allowed_numbers(evidence)
    tokens = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    for tok in tokens:
        try:
            num = float(tok)
        except ValueError:
            return False
        matched = False
        for a in allowed:
            if abs(num - a) < 1e-3 or (a != 0 and abs(num - a) / abs(a) < 1e-3):
                matched = True
                break
        if not matched:
            log.warning("narrative_hallucinated_number_detected", token=tok, allowed_sample=sorted(list(allowed))[:8])
            return False
    return True


def generate_template_reason(evidence: dict[str, Any]) -> tuple[str, str]:
    """Generate a deterministic ONE-sentence narrative and statutory cited rule fallback.

    Structure: classification + confidence band + 2 strongest evidences + rule/regulation + suggested action.
    """
    cls = evidence.get("cls", "FLARE")
    conf = float(evidence.get("conf", 0.0))
    lo = float(evidence.get("lo", 0.0))
    hi = float(evidence.get("hi", 0.0))
    is_suppressed = bool(evidence.get("offshore_suppressed", False))

    if is_suppressed:
        cited_rule = "OFFSHORE-SUPPRESSED"
        narrative = (
            f"{cls} alert suppressed with {conf:.2f} confidence [{lo:.2f}-{hi:.2f}] "
            f"driven by marine water landcover and zero inland facility proximity; "
            f"implicates offshore marine observation protocol; monitor subsequent orbital passes without ground dispatch."
        )
        return narrative, cited_rule

    # Determine rule and action
    if cls == "WILD" and evidence.get("landcover_class") == "forest":
        cited_rule = "MOEFCC-FOREST-FIRE"
        reg_desc = "MoEFCC forest-fire prevention protocol"
        action = "notify forest division officers and dispatch wildfire containment team"
    elif cls in STATUTORY_RULES:
        cited_rule, reg_desc, action = STATUTORY_RULES[cls]
    else:
        cited_rule = "GENERAL-ENVIRONMENTAL"
        reg_desc = "state pollution control environmental standards"
        action = "initiate on-ground verification survey"

    # Select the 2 strongest evidences grounded in available real fields
    t_k = int(round(evidence["t_fire_K"])) if (evidence.get("t_fire_K") is not None and evidence["t_fire_K"] > 0) else None
    ev_t = f"retrieved temperature of {t_k} K" if t_k is not None else None

    d_m = int(round(evidence["dist_facility_m"])) if (evidence.get("dist_facility_m") is not None) else None
    fac_name = evidence.get("facility_name") or evidence.get("facility_sector") or "industrial site"
    ev_dist = f"facility proximity of {d_m} m to {fac_name}" if d_m is not None else None

    n_days = int(evidence.get("n_days", 1))
    ev_days = f"persistent recurrence over {n_days} days" if n_days > 1 else None

    night_frac = float(evidence.get("night_frac", 0.0))
    ev_night = f"high nocturnal fraction of {night_frac:.2f}" if night_frac >= 0.5 else None

    frp_max = float(evidence.get("frp_max", 0.0))
    ev_frp = f"peak radiative power of {frp_max:.1f} MW" if frp_max > 0 else None

    co2e_rate = evidence.get("co2e_rate_tph")
    ev_co2e = f"estimated emission rate of {float(co2e_rate):.2f} t/h CO2e" if (co2e_rate is not None and float(co2e_rate) > 0) else None

    d_shape = evidence.get("diurnal_shape")
    ev_diurnal = f"{d_shape} diurnal cycle" if d_shape else None

    lc = evidence.get("landcover_class")
    ev_lc = f"{lc} landcover classification" if lc else None

    # Priority candidate ordering per class
    if cls == "FLARE":
        pool = [ev_t, ev_dist, ev_night, ev_diurnal, ev_co2e, ev_days, ev_frp, ev_lc]
    elif cls == "IND_FIRE":
        pool = [ev_frp, ev_dist, ev_t, ev_diurnal, ev_co2e, ev_days, ev_night, ev_lc]
    elif cls == "COAL":
        pool = [ev_days, ev_diurnal, ev_dist, ev_frp, ev_lc, ev_t, ev_co2e, ev_night]
    elif cls == "WILD":
        pool = [ev_lc, ev_diurnal, ev_frp, ev_days, ev_dist, ev_t, ev_night, ev_co2e]
    elif cls == "LEAK":
        pool = [ev_dist, ev_co2e, ev_days, ev_diurnal, ev_night, ev_frp, ev_t, ev_lc]
    else:
        pool = [ev_t, ev_frp, ev_dist, ev_days, ev_diurnal, ev_night, ev_co2e, ev_lc]

    active_evidences = [e for e in pool if e is not None]
    if len(active_evidences) >= 2:
        ev1, ev2 = active_evidences[0], active_evidences[1]
    elif len(active_evidences) == 1:
        ev1 = active_evidences[0]
        ev2 = "satellite radiative retrieval"
    else:
        ev1 = "satellite radiative retrieval"
        ev2 = "regional thermal anomaly signature"

    if cls == "LEAK":
        narrative = (
            f"candidate fugitive thermal anomaly - low confidence ({conf:.2f}) [{lo:.2f}-{hi:.2f}] "
            f"driven by {ev1} and {ev2}; "
            f"implicates {reg_desc}; {action}."
        )
    else:
        narrative = (
            f"{cls} alert confirmed with {conf:.2f} confidence [{lo:.2f}-{hi:.2f}] "
            f"driven by {ev1} and {ev2}; "
            f"implicates {reg_desc}; {action}."
        )
    return narrative, cited_rule


def _call_llm(provider: str, evidence: dict[str, Any], settings: Any) -> tuple[str, str] | None:
    """Invoke local or remote LLM with strict single-sentence and anti-hallucination prompt."""
    import httpx

    prompt = (
        "You are Agnivani's regulatory reasoning engine for satellite thermal alerts.\n"
        "Given the alert evidence dictionary below, output a JSON object with:\n"
        '1. "narrative": EXACTLY ONE sentence with format:\n'
        "   classification + confidence band [lo-hi] + 2 strongest evidences + rule/regulation implicated + suggested action.\n"
        '2. "cited_rule": machine tag (e.g. CPCB-FLARE-PERMIT, NDMA-INDUSTRIAL-SAFETY, DGMS-COAL-FIRE, CPCB-AGRICULTURAL-BURN, PNGRB-GAS-LEAK, OFFSHORE-SUPPRESSED).\n\n'
        "CRITICAL ANTI-HALLUCINATION REQUIREMENT:\n"
        "You must NEVER invent numbers. You may ONLY restate numbers provided in the evidence dictionary.\n"
        "Do not invent dates, years, sections, or ungrounded statistics. Ensure the narrative is ONE sentence ending with a period.\n\n"
        f"Evidence:\n{json.dumps(evidence, indent=2)}\n\n"
        'Respond ONLY with valid JSON: {"narrative": "...", "cited_rule": "..."}'
    )

    if provider == "ollama":
        url = f"{getattr(settings, 'ollama_url', 'http://localhost:11434').rstrip('/')}/api/generate"
        model = getattr(settings, "ollama_model", "llama3.2:1b")
        payload = {"model": model, "prompt": prompt, "stream": False, "format": "json"}
        with httpx.Client(timeout=2.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = json.loads(resp.json().get("response", "{}"))
                return data.get("narrative", "").strip(), data.get("cited_rule", "").strip()

    elif provider == "openai":
        api_key = getattr(settings, "openai_api_key", "") or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return None
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        with httpx.Client(timeout=2.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                return data.get("narrative", "").strip(), data.get("cited_rule", "").strip()

    elif provider == "anthropic":
        api_key = getattr(settings, "anthropic_api_key", "") or os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }
        with httpx.Client(timeout=2.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                content = resp.json()["content"][0]["text"]
                data = json.loads(content)
                return data.get("narrative", "").strip(), data.get("cited_rule", "").strip()

    return None


def generate_reason(evidence: dict[str, Any], settings: Any = None) -> tuple[str, str, str]:
    """Generate narrative reason, template fallback, and cited rule for an alert.

    Returns:
        (reason, reason_template, cited_rule)
    """
    reason_template, template_rule = generate_template_reason(evidence)

    # Check offline or template mode
    offline_mode = getattr(settings, "offline_mode", False)
    provider: Literal["auto", "ollama", "openai", "anthropic", "template"] = getattr(settings, "llm_provider", "auto")

    if offline_mode or provider == "template":
        return reason_template, reason_template, template_rule

    # Resolve provider if auto
    target_provider = provider
    if target_provider == "auto":
        if getattr(settings, "openai_api_key", "") or os.getenv("OPENAI_API_KEY", ""):
            target_provider = "openai"
        elif getattr(settings, "anthropic_api_key", "") or os.getenv("ANTHROPIC_API_KEY", ""):
            target_provider = "anthropic"
        elif os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_URL"):
            target_provider = "ollama"
        else:
            # Default to deterministic template without blocking or requiring paid key
            return reason_template, reason_template, template_rule

    try:
        llm_out = _call_llm(target_provider, evidence, settings)
        if llm_out:
            narrative, cited_rule = llm_out
            if narrative and validate_no_hallucinated_numbers(narrative, evidence):
                # Ensure narrative is single sentence
                cleaned_narrative = narrative.replace("\n", " ").strip()
                final_rule = cited_rule if cited_rule else template_rule
                return cleaned_narrative, reason_template, final_rule
            else:
                log.info("narrative_guard_fallback_to_template", reason="validation_failed_or_empty")
    except Exception as exc:
        log.debug("narrative_llm_invocation_failed", error=str(exc))

    return reason_template, reason_template, template_rule
