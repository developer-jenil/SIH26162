# AGNIVANI Cloud Deployment Guide

This guide details the step-by-step instructions for deploying the **AGNIVANI Industrial Thermal Intelligence Grid** to free cloud container hosts (**Render** as primary, **Hugging Face Spaces** as fallback) with zero code changes.

The container image serves the bundled Gujarat corridor dataset (41 detections, 2 industrial gas flares, 2 candidate fugitive leaks at Hazira LNG/Steel) in strict read-only, offline mode with no external paid API keys or writable database requirements.

---

## 1. Render Deployment (Primary — Exact 6 Clicks)

Render automatically detects the root `Dockerfile` and `render.yaml` blueprint.

### Step-by-Step Procedure
1. Log into your dashboard at [dashboard.render.com](https://dashboard.render.com) and click **New +** (top right).
2. Select **Web Service**.
3. Choose **Build and deploy from a Git repository**, click **Next**, and select your repository: `developer-jenil/SIH26162` (or connect your GitHub account).
4. Verify project settings:
   - **Name**: `agnivani` (or custom name)
   - **Region**: Singapore or Frankfurt (any region)
   - **Root Directory**: Leave blank (repository root)
   - **Runtime**: `Docker` (automatically detected)
   - **Instance Type / Plan**: Select **Free**
5. Add the 4 production Environment Variables (under **Environment Variables**):
   - `OFFLINE_MODE` = `true`
   - `AGNIVANI_READONLY_DB` = `1`
   - `SCORER_BACKEND` = `heuristic`
   - `LOG_LEVEL` = `INFO`
   *(Note: If you deploy via Render Blueprints using `render.yaml`, these environment variables and healthcheck are pre-configured automatically).*
6. Click **Deploy Web Service** (or **Create Web Service**).

- **Expected Build Time**: ~3 to 4 minutes (compiles GDAL C-extensions and installs Python packages via multi-stage wheel cache).
- **Expected URL Pattern**: `https://agnivani.onrender.com` (or `https://<your-service-name>.onrender.com`).

---

## 2. Free-Tier Keep-Alive Configuration (UptimeRobot)

Render free-tier web services spin down to sleep after ~15 minutes of inactivity. When a judge visits a sleeping container, the initial spin-up takes ~50 seconds (cold start).

To keep the container warm 24/7 during presentation and judging:
1. Create a free account at [uptimerobot.com](https://uptimerobot.com).
2. Click **Add New Monitor**.
3. Configure the monitor:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `AGNIVANI Production Health`
   - **URL (or IP)**: `https://<your-service-name>.onrender.com/api/health`
   - **Monitoring Interval**: `5 minutes`
4. Click **Create Monitor**.

UptimeRobot will ping `/api/health` every 5 minutes, preventing the container from idling or sleeping.

---

## 3. Hugging Face Spaces Deployment (Zero-Sleep Fallback)

If Render experiences queue delays or capacity limits, Hugging Face Spaces provides an immediate, zero-sleep alternative.

### Configuration
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. Space settings:
   - **Space Name**: `agnivani-grid`
   - **License**: `mit` or `apache-2.0`
   - **Select the Space SDK**: **Docker** -> **Blank**
   - **Space Hardware**: Free CPU basic (2 vCPU · 16 GB RAM)
   - **Visibility**: **Public**
3. Create the Space.
4. In the Space repository, ensure the `README.md` frontmatter contains **only**:
   ```yaml
   ---
   title: Agnivani Thermal Intelligence Grid
   emoji: 🔥
   colorFrom: cyan
   colorTo: blue
   sdk: docker
   pinned: false
   ---
   ```
   > **CRITICAL**: Do **NOT** set `app_port: 8000` in the YAML metadata! Hugging Face Spaces defaults to port 7860 and injects `PORT=7860` into the container environment. The AGNIVANI `Dockerfile` dynamically binds to `${PORT:-8000}`. If you force `app_port: 8000`, HF will proxy to a port that nothing is listening on.
5. Push the repository to the Space remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
   git push space main
   ```
6. **Note**: Hugging Face Spaces do not spin down on traffic idle.

---

## 4. Judge-Test Checklist (Mobile Device / Cellular Network)

Test the deployed URL from a smartphone connected to cellular data (external network) to verify full functionality:

- [ ] **Home Dashboard (`/`)**: Page loads with tactical dark HUD theme, active header telemetry chips, and status indicator `STALE (5-DAY NRT)`.
- [ ] **Hero Deep Link (`/?focus=AV-0B12A4B9`)**: URL deep link automatically selects Hazira LNG/Steel Flare #1, focuses the map centroid, and hydrates the Detection Inspector (`conf=0.900`, `T_fire=486.1 K`, `FRP=9.23 MW`).
- [ ] **Operational Preflight (`/preflight.html`)**: All 6 verification checks display `[PASS]` in green (DuckDB Store, Facilities Registry, Classification Scorer, Planck/Dozier Physical Inversion, ESA WorldCover, Hero Detections).
- [ ] **Scientific Provenance (`/api/provenance`)**: Returns JSON payload with 41 total detections, 4 matched detections, and empirical threshold disclosures.
- [ ] **Inspector & Console Hygiene**: Open browser developer tools / console — verify 0 errors, no Carto API key watermarks, and smooth map tile rendering (Esri World Imagery).

---

## 5. Presentation / Pitch Slides Links

Copy and paste these exact bullet points into your competition slide deck:

- **Live Operational Prototype**: `https://<your-service-name>.onrender.com`
- **Verified Flare Telemetry Deep Link**: `https://<your-service-name>.onrender.com/?focus=AV-0B12A4B9`
- *Note for evaluators: Hosted on a container cloud tier; initial cold load may take up to 45–60 seconds if waking from idle.*

---

## 6. Build Troubleshooting

If a cloud build fails, check these two common causes:

1. **GDAL / Rasterio C-Extension Compilation**:
   - *Symptom*: Build fails during `pip install rasterio` with missing `gdal-config` or header errors.
   - *Fix*: The repository's multi-stage `Dockerfile` handles this by installing `libgdal-dev` and `gdal-bin` in Debian `python:3.11-slim` before installing wheels, and copying the compiled `/install/pkgs` directory into the runtime stage.
2. **Repository / Asset Size Limits**:
   - *Symptom*: Git clone timeout or container image size rejection.
   - *Fix*: The entire repository and data payload (`data/agnivani.duckdb` + 3 corridor CSVs + parquet feature stores) is strictly optimized to ~7.1 MB total. `.dockerignore` excludes all test caches, virtualenvs, and intermediate files.
