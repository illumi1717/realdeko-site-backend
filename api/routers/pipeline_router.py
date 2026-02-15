"""
Router that exposes the AI pipeline (Instagram → AI → draft articles)
as an HTTP endpoint so it can be triggered from the admin UI.
"""

import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status

pipeline_router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# ── In-memory state for tracking a single pipeline run ──────────────────────

_lock = threading.Lock()

_state: dict = {
    "status": "idle",          # idle | running | completed | failed
    "started_at": None,        # ISO timestamp
    "finished_at": None,       # ISO timestamp
    "error": None,             # error message if failed
}


def _get_state() -> dict:
    with _lock:
        return _state.copy()


def _set_state(
    run_status: str,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    error: Optional[str] = None,
):
    with _lock:
        _state["status"] = run_status
        if started_at is not None:
            _state["started_at"] = started_at
        if finished_at is not None:
            _state["finished_at"] = finished_at
        _state["error"] = error


# ── Background runner ────────────────────────────────────────────────────────

# Resolve the absolute path to the ai-pipeline main.py.
# Layout: backend/api/routers/pipeline_router.py  →  backend/ai-pipeline/main.py
_AI_PIPELINE_DIR = Path(__file__).resolve().parents[2] / "ai-pipeline"
_AI_PIPELINE_SCRIPT = _AI_PIPELINE_DIR / "main.py"


def _run_pipeline():
    """Execute the AI pipeline script in a subprocess."""
    try:
        # Run with the same Python interpreter; set cwd so the pipeline's
        # relative imports (agent_module, services.*) work as expected.
        result = subprocess.run(
            [sys.executable, str(_AI_PIPELINE_SCRIPT)],
            cwd=str(_AI_PIPELINE_DIR),
            capture_output=True,
            text=True,
            timeout=600,  # 10-minute safety timeout
        )

        if result.returncode == 0:
            _set_state("completed", finished_at=datetime.utcnow().isoformat())
        else:
            stderr = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            _set_state("failed", finished_at=datetime.utcnow().isoformat(), error=stderr[-2000:])
    except subprocess.TimeoutExpired:
        _set_state("failed", finished_at=datetime.utcnow().isoformat(), error="Pipeline timed out (10 min limit)")
    except Exception as exc:
        _set_state("failed", finished_at=datetime.utcnow().isoformat(), error=str(exc)[:2000])


# ── Endpoints ────────────────────────────────────────────────────────────────

@pipeline_router.post("/run")
def run_pipeline():
    """
    Trigger the AI pipeline (Instagram sync → AI draft creation).
    Returns immediately; the pipeline runs in the background.
    """
    current = _get_state()
    if current["status"] == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pipeline is already running.",
        )

    _set_state("running", started_at=datetime.utcnow().isoformat(), finished_at=None, error=None)

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    return {"message": "Pipeline started", "started_at": _get_state()["started_at"]}


@pipeline_router.get("/status")
def pipeline_status():
    """Return the current state of the pipeline."""
    return _get_state()


