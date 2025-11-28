# errors/error_parser.py
"""
Multi-Language Error Parser: Python, JavaScript, Java
"""

import re
from errors.error_types import ErrorType


def parse_error(stderr: str, code: str = "", language: str = "python"):
    language = (language or "python").lower()
    text = stderr or ""

    # ------------------ PYTHON ------------------
    if language == "python":
        if not text.strip():
            return ErrorType.NONE, ""

        if "SyntaxError" in text:
            return ErrorType.SYNTAX, text
        if "NameError" in text:
            return ErrorType.NAME, text
        if "IndexError" in text:
            return ErrorType.INDEX, text
        if "KeyError" in text:
            return ErrorType.KEY, text
        if "AttributeError" in text:
            return ErrorType.ATTRIBUTE, text
        if "ZeroDivisionError" in text:
            return ErrorType.ZERO_DIVISION, text
        if "RecursionError" in text:
            return ErrorType.RECURSION, text
        if "Traceback" in text:
            return ErrorType.RUNTIME, text

        return ErrorType.RUNTIME, text


    # ------------------ JAVASCRIPT ------------------
    if language in ("js", "javascript", "node"):
        if not text.strip():
            return ErrorType.NONE, ""

        if "SyntaxError" in text:
            return ErrorType.SYNTAX, text
        if "ReferenceError" in text:
            return ErrorType.NAME, text
        if "TypeError" in text:
            return ErrorType.TYPE, text
        if "RangeError" in text:
            return ErrorType.INDEX, text
        if "unexpected token" in text.lower():
            return ErrorType.SYNTAX, text
        if "is not defined" in text.lower():
            return ErrorType.NAME, text

        return ErrorType.RUNTIME, text


    # ------------------ JAVA ------------------
    if language == "java":
        if not text.strip():
            return ErrorType.NONE, ""

        if "error:" in text:
            return ErrorType.SYNTAX, text
        if "NullPointerException" in text:
            return ErrorType.ATTRIBUTE, text
        if "ArrayIndexOutOfBoundsException" in text:
            return ErrorType.INDEX, text
        if "cannot find symbol" in text:
            return ErrorType.NAME, text
        if "Exception in thread" in text:
            return ErrorType.RUNTIME, text

        return ErrorType.RUNTIME, text


    return ErrorType.RUNTIME, text
