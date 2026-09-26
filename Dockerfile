# ==============================================================================
# AGNIVANI Multi-Stage Production Dockerfile (P8 Deployment Readiness)
# ==============================================================================

# --- Stage 1: Build Dependencies ---
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/pkgs -r requirements.txt

# --- Stage 2: Runtime Environment ---
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.local/bin:/install/pkgs/bin:${PATH}" \
    PYTHONPATH="/install/pkgs/lib/python3.11/site-packages:/app" \
    PORT=8000 \
    OFFLINE_MODE=true \
    AGNIVANI_READONLY_DB=1 \
    SCORER_BACKEND=heuristic \
    LOG_LEVEL=INFO

# Install runtime shared libraries for GDAL/Rasterio/XGBoost
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgdal-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user creation for security
RUN groupadd -g 1001 agnivani && \
    useradd -u 1001 -g agnivani -s /bin/bash -m agnivani

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install/pkgs /install/pkgs

# Copy application source, static assets, and scripts
COPY --chown=agnivani:agnivani agnivani/ /app/agnivani/
COPY --chown=agnivani:agnivani css/ /app/css/
COPY --chown=agnivani:agnivani js/ /app/js/
COPY --chown=agnivani:agnivani scripts/ /app/scripts/
COPY --chown=agnivani:agnivani index.html /app/index.html
COPY --chown=agnivani:agnivani preflight.html /app/preflight.html
COPY --chown=agnivani:agnivani dossier.html /app/dossier.html
COPY --chown=agnivani:agnivani facility.html /app/facility.html
COPY --chown=agnivani:agnivani requirements.txt /app/requirements.txt
COPY --chown=agnivani:agnivani Makefile /app/Makefile

# Create data directories and explicitly copy data assets (no blanket COPY .)
RUN mkdir -p /app/data/processed /app/data/raw/firms /app/data/raw/registry /app/data/models && \
    chown -R agnivani:agnivani /app/data

COPY --chown=agnivani:agnivani data/agnivani.duckdb /app/data/agnivani.duckdb
COPY --chown=agnivani:agnivani data/processed/*.parquet /app/data/processed/
COPY --chown=agnivani:agnivani data/raw/firms/*.csv /app/data/raw/firms/
COPY --chown=agnivani:agnivani data/raw/registry/*.json /app/data/raw/registry/
COPY --chown=agnivani:agnivani data/models/ /app/data/models/

USER agnivani

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

CMD ["sh", "-c", "uvicorn agnivani.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
