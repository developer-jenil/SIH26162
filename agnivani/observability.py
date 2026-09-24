"""Wall-clock telemetry and tracing for the 6-stage evidence trail and pipeline logs."""
from __future__ import annotations
import time
from contextlib import contextmanager
from typing import Iterator
import pandas as pd

LABELS = [
    "VIIRS INGEST",
    "INDIA FILTER",
    "SOURCE CLUSTER",
    "PLANCK RETRIEVAL",
    "REGISTRY JOIN",
    "CLASSIFY",
]

class StageTracer:
    """Accumulates real per-stage wall-clock timings for the 6-stage evidence trail."""

    def __init__(self):
        self.stage_timings: dict[str, int] = {}

    @contextmanager
    def stage(self, label: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            t1 = time.perf_counter()
            delta_ms = (t1 - t0) * 1000.0
            # Record measured wall-clock milliseconds, strictly positive
            self.stage_timings[label] = max(1, int(round(delta_ms)))

    def record_ms(self, label: str, ms: int | float) -> None:
        """Manually record a measured duration for a stage."""
        self.stage_timings[label] = max(1, int(round(ms)))

    def get_ms(self, label: str) -> int:
        return self.stage_timings.get(label, 1)

    def to_evidence(self, source, feature, score) -> list[dict]:
        """Convert accumulated timings into the 6-stage evidence trail."""
        values = [
            f"{source.n_hits} detections",
            f"centroid inside mainland",
            f"{source.n_days} days / {source.n_hits} hits",
            f"T={feature.t_fire_K:.0f} K" if pd.notna(feature.t_fire_K) else "retrieval unresolved",
            feature.facility_name or "no facility within 10 km",
            f"{score.cls} p={score.conf:.2f}",
        ]
        evidence = []
        for i, label in enumerate(LABELS, 1):
            ms_val = self.get_ms(label)
            if ms_val <= 0:
                ms_val = 1
            status = "warn" if i in (4, 5) and "no " in values[i - 1] else "ok"
            evidence.append({
                "stage": i,
                "label": label,
                "status": status,
                "detail": values[i - 1],
                "value": values[i - 1],
                "ms": ms_val,
            })
        return evidence
