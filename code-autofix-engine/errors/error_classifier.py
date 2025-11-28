# errors/error_classifier.py
from errors.error_types import ErrorType

# AST-first categories (fast deterministic fixes)
AST_FIRST = {
    ErrorType.SYNTAX,
    ErrorType.NAME,
    ErrorType.IMPORT,
    ErrorType.ATTRIBUTE,
    ErrorType.KEY,
    ErrorType.VALUE,
    ErrorType.FILE,
    ErrorType.PARSE,
    ErrorType.REGEX,
    ErrorType.ENCODING,
}

# LLM-first / require reasoning
LLM_FIRST = {
    ErrorType.LOGICAL,
    ErrorType.RECURSION,
    ErrorType.RUNTIME,
    ErrorType.ZERO_DIVISION,
    ErrorType.ARITHMETIC,
    ErrorType.NETWORK,
    ErrorType.SYSTEM,
    ErrorType.MEMORY,
}

def choose_fix_method(error_type: str) -> str:
    """Return 'AST' or 'LLM' depending on error_type."""
    if error_type in AST_FIRST:
        return "AST"
    if error_type in LLM_FIRST:
        return "LLM"
    # default to LLM for tricky or unknown
    return "LLM"

# compatibility: some callers used classify_error(stdout, stderr)
def classify_error(stdout: str, stderr: str, code: str = "") -> str:
    """
    Backwards-compatible wrapper: run parse_error logic via error_parser.
    """
    from errors.error_parser import parse_error
    err, _ = parse_error(stderr, code)
    return err
