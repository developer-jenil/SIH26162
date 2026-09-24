.PHONY: help install serve test lint preflight run-pipeline demo record

ifeq ($(OS),Windows_NT)
    PYTHON ?= $(wildcard .venv/Scripts/python.exe)
    ifeq ($(PYTHON),)
        PYTHON = python
    endif
else
    PYTHON ?= $(wildcard .venv/bin/python)
    ifeq ($(PYTHON),)
        PYTHON = python3
    endif
endif

help:
	@echo "AGNIVANI Operational Command Interface"
	@echo "  make install      - Install Python package dependencies"
	@echo "  make serve        - Launch FastAPI backend server"
	@echo "  make test         - Run full pytest test suite"
	@echo "  make lint         - Run syntax verification and linting"
	@echo "  make preflight    - Run operational preflight verification"
	@echo "  make run-pipeline - Run end-to-end 6-stage ingestion pipeline"
	@echo "  make demo         - Launch demo hero deep link in browser"
	@echo "  make record       - Preflight and pipeline execution for recording"

install:
	$(PYTHON) -m pip install -r requirements.txt

serve:
	$(PYTHON) -m uvicorn agnivani.api.server:create_app --factory --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest -v

lint:
	$(PYTHON) -m compileall agnivani scripts tests

preflight:
	$(PYTHON) scripts/preflight.py

run-pipeline:
	$(PYTHON) scripts/run_pipeline.py

demo:
	$(PYTHON) -c "import webbrowser; webbrowser.open('http://localhost:8000?focus=AV-0B12A4B9')"

record:
	$(PYTHON) scripts/preflight.py
	$(PYTHON) scripts/run_pipeline.py
