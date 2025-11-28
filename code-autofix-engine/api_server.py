# api_server.py
"""
FastAPI wrapper for the Python-only Local Code Auto-Fix Engine.

Provides two endpoints:
 - POST /run
     * Run the provided Python code once in the sandbox and return stdout/stderr + parsed error info.
 - POST /repair
     * Run the full repair loop and return the final code, parsed errors and the change-log/report.

This implementation assumes the project is single-language (Python) and that the following modules exist
and are importable in the project:
 - runtime.sandbox_runner.run_in_sandbox(code: str) -> (stdout: str, stderr: str)
 - errors.error_parser.parse_error(stderr: str, code: str) -> (error_type: str, full_error: str)
 - iterations.iteration_controller.run_repair_loop(original_code: str, user_prompt: str, max_iterations: int) -> (final_code, report_path)
 - config.settings.MAX_ITERATIONS
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
import json
import logging
import os

from runtime.sandbox_runner import run_in_sandbox
from errors.error_parser import parse_error
from iterations.iteration_controller import run_repair_loop
from config.settings import MAX_ITERATIONS
from utils.logger import log_header, log_step
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("api_server")
logger.setLevel(logging.INFO)

app = FastAPI(title="Local Code Auto-Fix Engine (Python-only API)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Request / Response Models
# -------------------------
class RunRequest(BaseModel):
    code: str


class RunResponse(BaseModel):
    stdout: Optional[str]
    stderr: Optional[str]
    error_type: str
    full_error: Optional[str]


class RepairRequest(BaseModel):
    code: str
    prompt: str
    max_iterations: Optional[int] = None


class RepairResponse(BaseModel):
    final_code: str
    report_path: Optional[str]
    parsed_error: Optional[Dict[str, Any]]
    changes: Optional[Any] = None
    raw_report: Optional[Dict[str, Any]] = None


# -------------------------
# Utility
# -------------------------
def _load_json_report(path: str) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    try:
        if not os.path.exists(path):
            logger.warning("Report path does not exist: %s", path)
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Failed to load report JSON: %s", e)
        return None


# -------------------------
# Endpoints
# -------------------------
@app.post("/run", response_model=RunResponse)
def run_once(payload: RunRequest):
    """
    Execute the provided Python code once in the sandbox and return stdout/stderr
    along with a parsed error classification.
    """
    code = payload.code or ""
    if not code.strip():
        raise HTTPException(status_code=400, detail="Empty code provided.")

    log_header("API /run called")
    log_step("Executing sandbox run")

    try:
        stdout, stderr = run_in_sandbox(code)
    except Exception as e:
        logger.exception("Sandbox execution failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Sandbox execution failed: {e}")

    try:
        error_type, full_err = parse_error(stderr, code)
    except Exception as e:
        logger.exception("Error parsing failed: %s", e)
        # fallback: return raw stderr with UNKNOWN
        error_type, full_err = "UNKNOWN", stderr

    return RunResponse(
        stdout=stdout,
        stderr=stderr,
        error_type=error_type,
        full_error=full_err,
    )


@app.post("/repair", response_model=RepairResponse)
def repair(payload: RepairRequest):
    """
    Run the full repair loop over the provided Python code using the user prompt.
    Returns the final code, path to saved report, parsed top-level error and changes.
    """
    code = payload.code or ""
    prompt = payload.prompt or ""
    max_iter = payload.max_iterations or MAX_ITERATIONS

    if not code.strip():
        raise HTTPException(status_code=400, detail="Empty code provided.")
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Empty prompt provided.")

    log_header("API /repair called")
    log_step("Starting repair loop")

    try:
        final_code, report_path = run_repair_loop(original_code=code, user_prompt=prompt, max_iterations=max_iter)
    except Exception as e:
        logger.exception("Repair loop failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Repair loop failed: {e}")

    # Try to load the iteration report JSON if available to extract changes and top errors
    report_json = _load_json_report(report_path) if report_path else None

    # Attempt to summarize the last iteration's error info in a friendly structure
    parsed_error = None
    changes = None
    if report_json:
        try:
            parsed_error = {}
            total_iters = report_json.get("total_iterations", len(report_json.get("iterations", [])))
            parsed_error["final_status"] = report_json.get("final_status")
            parsed_error["total_iterations"] = total_iters

            # Extract last iteration info if present
            iters = report_json.get("iterations", [])
            if iters:
                last = iters[-1]
                parsed_error["last_iteration"] = {
                    "iteration": last.get("iteration"),
                    "error_type": last.get("error_type"),
                    "fix_method": last.get("fix_method"),
                    "stdout": last.get("stdout"),
                    "stderr": last.get("stderr"),
                }

            # Prefer named keys for changes: 'changes' or 'changeLog'
            changes = report_json.get("changes") or report_json.get("changeLog") or report_json.get("diffs") or []
        except Exception as e:
            logger.exception("Failed to extract report summary: %s", e)

    return RepairResponse(
        final_code=final_code,
        report_path=report_path,
        parsed_error=parsed_error,
        changes=changes,
        raw_report=report_json,
    )


# -------------------------
# Run server
# -------------------------
if __name__ == "__main__":
    import uvicorn

    # Note: set host/port as needed. Do not use --reload in production.
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, log_level="info")
