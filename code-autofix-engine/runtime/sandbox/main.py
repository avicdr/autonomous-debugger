# sandbox/main.py
"""
Cross-platform secure sandbox for running untrusted Python code.

Supports:
- Linux/macOS: CPU + memory limits (resource module)
- Windows: safe execution without preexec_fn and without resource limits

This file is launched by sandbox_runner.py.
"""

import subprocess
import sys
import os
import tempfile
import logging
import platform


# ----------------------------
# Logging Setup
# ----------------------------
logger = logging.getLogger("sandbox")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s",
                                  "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# ----------------------------
# Configurable Limits
# ----------------------------
TIME_LIMIT = int(os.getenv("SANDBOX_TIME_LIMIT", 5))          # seconds
MEMORY_LIMIT_MB = int(os.getenv("SANDBOX_MEMORY_LIMIT_MB", 128))  # MB

IS_WINDOWS = platform.system().lower().startswith("win")
IS_POSIX = os.name == "posix"


# ----------------------------
# POSIX Resource Limiting (Linux/macOS)
# ----------------------------
def limit_resources():
    """
    Apply CPU + memory limits ONLY on POSIX (Linux/macOS).
    Windows does NOT support resource module or preexec_fn.
    """
    if not IS_POSIX:
        return  # no limits on Windows

    try:
        import resource
        # CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (TIME_LIMIT, TIME_LIMIT))
        # Memory limit
        mem_bytes = MEMORY_LIMIT_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception as e:
        logger.warning(f"Failed to apply resource limits: {e}")


# ----------------------------
# Sandbox Execution
# ----------------------------
def run_code_in_sandbox(code: str):
    """
    Securely execute Python code cross-platform.

    Returns:
        stdout (str)
        stderr (str)
    """
    tmp_file_path = None

    try:
        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
            tmp_file.write(code)
            tmp_file.flush()
            tmp_file_path = tmp_file.name

        logger.info(f"Executing sandboxed code: {tmp_file_path}")

        # Build subprocess command
        cmd = [sys.executable, tmp_file_path]

        # POSIX: use preexec_fn + resource limits
        if IS_POSIX:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=limit_resources,
                text=True
            )
        else:
            # WINDOWS: preexec_fn NOT supported → run normally
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        try:
            stdout, stderr = proc.communicate(timeout=TIME_LIMIT + 1)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = "", "Error: Execution timed out."
            logger.warning("Execution timed out.")

    except Exception as e:
        logger.error(f"Sandbox crash: {e}")
        stdout, stderr = "", f"Sandbox internal error: {e}"

    finally:
        # Always clean up temp file
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

    return stdout, stderr


# ----------------------------
# STDIN Endpoint
# ----------------------------
if __name__ == "__main__":
    """
    Executed by sandbox_runner.py.
    Reads code from STDIN and prints machine-friendly output.
    """
    try:
        code = sys.stdin.read()
        if not code.strip():
            print("===STDOUT===\n")
            print("===STDERR===\nNo code provided.")
            sys.exit(0)

        stdout, stderr = run_code_in_sandbox(code)

        print("===STDOUT===")
        print(stdout)
        print("===STDERR===")
        print(stderr)

    except Exception as e:
        print("===STDOUT===\n")
        print("===STDERR===")
        print(f"Sandbox internal failure: {e}")
