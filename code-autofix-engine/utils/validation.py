"""
Validation functions for repair iterations.
Handles:
- Detecting real Python errors
- Ignoring sandbox log noise
- Determining whether the code is successfully fixed
"""

from errors.error_types import ErrorType


def clean_stderr(stderr: str) -> str:
    """
    Remove sandbox logger lines such as:
    [2025-11-27 13:34:39] [INFO] Executing sandboxed code...
    """
    cleaned = []
    for line in stderr.splitlines():
        stripped = line.strip()

        # Ignore timestamped sandbox logs
        if stripped.startswith("[20") and "] [INFO]" in stripped:
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def is_success(stdout: str, stderr: str, error_type: ErrorType) -> bool:
    """
    Determine if execution is successful.

    Success if:
    - error_type == NONE
    - cleaned stderr is empty or contains harmless warnings
    """
    if error_type != ErrorType.NONE:
        return False

    cleaned = clean_stderr(stderr)

    # If cleaned stderr is empty → success
    if cleaned == "":
        return True

    # Allow harmless warnings
    harmless = ["warning", "deprecated"]
    if any(h in cleaned.lower() for h in harmless):
        return True

    return False


def validate_iteration(stdout: str, stderr: str, error_type: ErrorType):
    """
    Main validation entry point.
    Returns:
        (bool success, str message)
    """
    success = is_success(stdout, stderr, error_type)

    if success:
        return True, "Execution succeeded."

    # Failure categories
    cleaned = clean_stderr(stderr).lower()

    if "syntaxerror" in cleaned:
        return False, "SyntaxError detected."
    if "indentationerror" in cleaned:
        return False, "IndentationError detected."
    if "memoryerror" in cleaned:
        return False, "MemoryError: exceeded limit."
    if "timeout" in cleaned or "timed out" in cleaned:
        return False, "Execution timed out."

    # If there is no stdout and no meaningful stderr
    if not stdout.strip() and cleaned.strip() == "":
        return False, "Code produced no output."

    return False, "Errors remain."
