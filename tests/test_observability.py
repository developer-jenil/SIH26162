import pytest
import time
from agnivani.observability import StageTracer, LABELS

def test_stage_tracer_records_positive_ms():
    tracer = StageTracer()
    with tracer.stage("VIIRS INGEST"):
        time.sleep(0.005)
    with tracer.stage("INDIA FILTER"):
        time.sleep(0.002)

    assert tracer.get_ms("VIIRS INGEST") >= 1
    assert tracer.get_ms("INDIA FILTER") >= 1
    # Check default fallback is at least 1, never 0
    assert tracer.get_ms("SOURCE CLUSTER") >= 1

class DummyObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def get(self, key, default=None):
        return getattr(self, key, default)

def test_evidence_never_has_zero_ms():
    tracer = StageTracer()
    with tracer.stage("VIIRS INGEST"):
        time.sleep(0.003)
    tracer.record_ms("INDIA FILTER", 2)
    tracer.record_ms("SOURCE CLUSTER", 5)
    tracer.record_ms("PLANCK RETRIEVAL", 10)
    tracer.record_ms("REGISTRY JOIN", 4)
    tracer.record_ms("CLASSIFY", 12)

    source = DummyObj(n_hits=5, n_days=2, centroid_lat=20.0, centroid_lon=75.0, ti4_median=340.0, ti5_median=295.0, pixel_area_m2=375**2)
    feature = DummyObj(t_fire_K=1500.0, facility_name="Test Plant", dist_facility_m=1200.0)
    score = DummyObj(cls="FLARE", conf=0.90)

    evidence = tracer.to_evidence(source, feature, score)
    assert len(evidence) == 6
    for stage in evidence:
        assert stage["ms"] > 0
        assert isinstance(stage["ms"], int)
        assert stage["stage"] in range(1, 7)
        assert stage["label"] in LABELS
