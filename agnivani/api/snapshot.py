"""Single-call snapshot endpoint for dashboard first paint."""
import json
from fastapi import APIRouter, Request, Response
from .schemas import StatsOut
from agnivani.models.scorer import CLASSES
router = APIRouter()

@router.get("/snapshot")
def snapshot(request: Request, response: Response, demo: bool = False):
    """Return stats, detections, and facilities in one round trip."""
    response.headers["X-Agnivani-Mode"] = "demo" if demo else "live"
    store = request.app.state.store
    scorer_meta = request.app.state.scorer.metadata()

    # Stats
    items = store.detections()
    by_class = {c: 0 for c in CLASSES}
    by_severity = {s: 0 for s in ["CRITICAL", "HIGH", "MODERATE", "LOW"]}
    last_ingest = None
    for x in items:
        by_class[x["cls"]] = by_class.get(x["cls"], 0) + 1
        by_severity[x["severity"]] = by_severity.get(x["severity"], 0) + 1
        ts = x["ts"]
        if last_ingest is None or ts > last_ingest:
            last_ingest = ts

    stats = StatsOut(
        total_detections=len(items),
        total_sources=len(items),
        by_class=by_class,
        by_severity=by_severity,
        last_ingest_utc=last_ingest,
        scorer=scorer_meta,
        coverage_pct=None,
    )

    # Facilities (already stored as plain dicts from payload)
    rows = store.query("SELECT payload FROM facilities")
    facilities = [json.loads(r) for r in rows.payload.tolist()] if not rows.empty else []

    return {
        "stats": stats.model_dump(),
        "detections": items,
        "facilities": facilities,
    }
