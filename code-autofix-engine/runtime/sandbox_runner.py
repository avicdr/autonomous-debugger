# runtime/sandbox_runner.py
"""
Multi-Language Sandbox Runner for Python / JS / Java
"""

import subprocess
import tempfile
import os
import sys
import shutil

DEFAULT_TIMEOUT = 5.0


def run_in_sandbox(code: str, language: str = "python", timeout: float = DEFAULT_TIMEOUT):
    lang = (language or "python").lower()

    if lang == "python":
        return run_python(code, timeout)
    if lang in ("js", "javascript", "node"):
        return run_js(code, timeout)
    if lang == "java":
        return run_java(code, timeout)

    return "", f"Unsupported language: {language}"


# ------------------ PYTHON ------------------

def run_python(code, timeout):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name

    try:
        p = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    finally:
        os.unlink(path)


# ------------------ JAVASCRIPT ------------------

def run_js(code, timeout):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(code)
        path = f.name

    try:
        p = subprocess.run(
            ["node", path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    finally:
        os.unlink(path)


# ------------------ JAVA ------------------

def run_java(code, timeout):
    folder = tempfile.mkdtemp()
    src_file = os.path.join(folder, "Main.java")

    with open(src_file, "w") as f:
        f.write(code)

    # Compile
    try:
        compile_proc = subprocess.run(
            ["javac", src_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=folder,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(folder)
        return "", "TIMEOUT"

    if compile_proc.stderr:
        shutil.rmtree(folder)
        return "", compile_proc.stderr

    # Run
    try:
        run_proc = subprocess.run(
            ["java", "-cp", folder, "Main"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=folder,
        )
        return run_proc.stdout, run_proc.stderr
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    finally:
        shutil.rmtree(folder)
