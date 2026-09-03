# AGNIVANI Backend

Offline-first FastAPI backend for the AGNIVANI Industrial Thermal Anomaly Intelligence Grid (SIH 2026, PS 26162). It ingests NASA FIRMS VIIRS NOAA-20/NOAA-21 area CSVs, filters mainland India, clusters persistent sources, performs a dual-band Planck/Dozier retrieval, joins an industrial registry, scores sources, persists them in DuckDB, and exposes REST plus Server-Sent Events.

## 30-second setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn agnivani.main:app
```

Open <http://localhost:8000/> for the dashboard or <http://localhost:8000/docs> for OpenAPI.

The example configuration uses `OFFLINE_MODE=true` and boots solely from the bundled real `data/raw/firms/firms_india.csv`. To fetch current observations, set `OFFLINE_MODE=false`, place your 32-character NASA FIRMS key in `FIRMS_MAP_KEY`, then run `python -m scripts.fetch_firms --days 5`. Raw pulls are resumable and limited to the FIRMS API's five-day maximum.

## Useful commands

```powershell
python -m pytest -q
python -m agnivani.models.train --dry-run
python -m scripts.build_registry
```

The default scorer is deterministic heuristic mode and explicitly reports that confidence values are hand-set priors. XGBoost mode safely falls back when trained artifacts are absent. Training requires independently labelled `data/processed/labelled.parquet`; heuristic-generated labels are never accepted as ground truth.

## API

- `GET /api/health`
- `GET /api/detections` (`bbox`, `hours`, repeatable `cls`, `min_conf`, `limit`)
- `GET /api/detections/{id}`
- `GET /api/stats`
- `GET /api/facilities?sector=`
- `GET /api/stream` (detection/ingest events and 15-second heartbeat)
- `POST /api/dispatch` (use `channel: "mock"` for a local JSONL receipt)
- `GET /api/pipeline/log`

CORS permits all origins because this is a local hackathon build. Restrict origins and configure real authenticated dispatch adapters before production use.
