import os
import subprocess
import sys

env = os.environ.copy()
env["AGNIVANI_READONLY_DB"] = "1"
env["OFFLINE_MODE"] = "true"
env["SCORER_BACKEND"] = "heuristic"
env["LOG_LEVEL"] = "INFO"

subprocess.run([sys.executable, "-m", "uvicorn", "agnivani.main:app", "--host", "0.0.0.0", "--port", "8000"], env=env)
