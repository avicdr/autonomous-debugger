# fixer/ssr_fixer.py
"""
SSR_Fixer v1 — Structural Semantic Repair (Mode A: Close + Split)

Purpose:
- Detect broken multiline literals / expressions that accidentally continue onto the next line,
  e.g.:
      numbers = [1, 2, 3, 4
      print(sum(numbers))]
  and repair to:
      numbers = [1, 2, 3, 4]
      print(sum(numbers))

- The module is intentionally conservative: it tries small, reversible edits and validates
  with ast.parse after each change. It prefers turning the trailing lines into separate
  statements (Mode A) rather than merging them into the literal.

How to use:
    from fixer.ssr_fixer import apply_ssr_fix
    fixed_code = apply_ssr_fix(original_code)

Notes:
- This module does NOT attempt to replace user intent with risky merges (Mode B). It implements
  the safe/default Mode A split behavior described above.
- It is designed to be run BEFORE AST-based repair so that AST tools receive syntactically valid code.
"""

from __future__ import annotations

import ast
import logging
import re
from typing import List, Tuple, Optional

logger = logging.getLogger("repair_system.ssr")
if not logger.handlers:
    # lightweight console handler if none configured externally
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(ch)
logger.setLevel(logging.INFO)


# ---------------------------
# Utilities
# ---------------------------

OPENERS = {"[": "]", "(": ")", "{": "}"}
CLOSERS = {v: k for k, v in OPENERS.items()}


def _safe_parse(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except Exception:
        return False


def _first_unclosed_opener_in_line(line: str) -> Optional[Tuple[int, str]]:
    """
    Return (index, opener_char) of the first opener in line that doesn't have a matching closer
    within the same line.
    If all openers are matched in that line, return None.
    This is a heuristic — multi-line brackets are typical, so we detect openers
    that probably start a multi-line literal.
    """
    stack = []
    for i, ch in enumerate(line):
        if ch in OPENERS:
            stack.append((i, ch))
        elif ch in OPENERS.values():
            if stack and OPENERS.get(stack[-1][1]) == ch:
                stack.pop()
            else:
                # unmatched closer: ignore
                pass
    if stack:
        # return earliest unmatched opener
        return stack[0]
    return None


def _line_is_likely_statement_start(line: str) -> bool:
    """
    Heuristic to determine if a line (after stripping) looks like the start of a new statement,
    e.g., 'print(', 'for ', 'if ', 'return ', 'x =', an identifier, etc.
    This helps us decide to split the next line out of the literal.
    """
    s = line.lstrip()
    if not s:
        return False
    keywords = ("def ", "class ", "for ", "if ", "while ", "try:", "with ", "return ", "import ", "from ", "print(", "print ")
    if s.startswith(keywords):
        return True
    # simple assignment or function call
    if re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*=", s):
        return True
    if re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*\(", s):  # foo(...
        return True
    # bare identifier / literal — also often statement start
    if re.match(r"^[A-Za-z_0-9'\"`]", s):
        return True
    return False


# ---------------------------
# Core SSR transforms
# ---------------------------

def _close_opener_on_line(line: str, opener_idx: int, opener_char: str) -> str:
    """
    Insert the corresponding closer at the end of the line if not present.
    Does minimal whitespace cleanup: ensure not to split tokens.
    Returns modified line.
    """
    closer = OPENERS[opener_char]
    # If line already contains closer after opener index, assume it's okay
    if closer in line[opener_idx:]:
        return line
    # Append closer before any inline comment
    if "#" in line:
        code_part, comment = line.split("#", 1)
        return code_part.rstrip() + closer + "  #" + comment
    else:
        return line.rstrip() + closer


def _dedent_line(line: str, indent_to_remove: int) -> str:
    """
    Remove up to indent_to_remove spaces from the start of the line (not tabs).
    Conservative: only remove spaces.
    """
    i = 0
    removed = 0
    while removed < indent_to_remove and i < len(line) and line[i] == " ":
        i += 1
        removed += 1
    return line[i:]


def _split_out_of_literal(lines: List[str], start_idx: int) -> List[str]:
    """
    Given lines and index 'start_idx' where line contains an opener that is unclosed,
    attempt to:
      - Close the opener on that start line (append the closer).
      - Move following lines that logically belong to 'outside' into new separate statements by dedenting.
    Returns new lines list (works on copy).
    """
    new_lines = list(lines)
    start_line = new_lines[start_idx]
    opener_info = _first_unclosed_opener_in_line(start_line)
    if not opener_info:
        return new_lines  # nothing to do

    opener_idx, opener_char = opener_info
    closer = OPENERS[opener_char]

    logger.debug(f"SSR: Found unclosed opener '{opener_char}' on line {start_idx}: '{start_line.strip()}'")

    # 1) Close opener on the same line
    new_start = _close_opener_on_line(start_line, opener_idx, opener_char)
    new_lines[start_idx] = new_start

    # 2) If the next line looks like it should be a new statement, ensure it is dedented
    if start_idx + 1 < len(new_lines):
        next_line = new_lines[start_idx + 1]
        # Compute base indent of start line
        base_indent = len(start_line) - len(start_line.lstrip())
        # If next_line indent <= base_indent OR next_line looks like a statement start, dedent it
        if (len(next_line) - len(next_line.lstrip()) <= base_indent) or _line_is_likely_statement_start(next_line):
            # remove base_indent spaces if present, else remove up to 4 spaces
            remove = base_indent if base_indent > 0 else 4
            new_lines[start_idx + 1] = _dedent_line(next_line, remove)
            logger.debug(f"SSR: Dedented line {start_idx+1} by {remove} spaces.")
    return new_lines


def _find_last_openers(lines: List[str]) -> List[Tuple[int, int, str]]:
    """
    Find lines that contain an opener that is likely unclosed across subsequent lines.
    Returns list of tuples: (line_index, opener_pos, opener_char)
    We'll prefer lines where opener is near the end (likely to start multi-line literal).
    """
    results = []
    for idx, ln in enumerate(lines):
        res = _first_unclosed_opener_in_line(ln)
        if res:
            opener_pos, opener_char = res
            results.append((idx, opener_pos, opener_char))
    return results


# ---------------------------
# High-level API
# ---------------------------

def apply_ssr_fix(code: str, max_attempts: int = 4) -> str:
    """
    Apply Structural Semantic Repairs (Mode A: Close + Split).
    Iteratively attempts to repair the code by:
      - scanning for likely unclosed openers
      - closing them on their start line
      - dedenting following lines if necessary
      - validating with ast.parse after each attempt
    Stops when code parses or when attempts exhausted.

    Returns the (possibly) fixed code.
    """
    if not code:
        return code

    working = code.replace("\r\n", "\n")
    if _safe_parse(working):
        return working

    lines = working.split("\n")

    for attempt in range(max_attempts):
        logger.debug(f"SSR attempt {attempt+1}/{max_attempts}")

        openers = _find_last_openers(lines)
        if not openers:
            # nothing to try
            logger.debug("SSR: no unclosed openers found.")
            break

        # Sort openers by line index (earliest first). We'll try earliest first.
        openers.sort(key=lambda x: x[0])

        changed = False
        for (line_idx, op_pos, op_char) in openers:
            # Try to close this opener and dedent next line(s)
            candidate_lines = _split_out_of_literal(lines, line_idx)
            candidate_code = "\n".join(candidate_lines)
            if candidate_code != "\n".join(lines):
                # test parse
                if _safe_parse(candidate_code):
                    logger.info(f"SSR: fixed by closing opener on line {line_idx+1}")
                    return candidate_code
                # Keep the change if it reduces syntax errors heuristically:
                # Compare lengths of parser exception messages? To keep simple, accept the change if it didn't make parse worse:
                # We'll check by trying a second stage healing: if parse still fails, but change reduced the number of total unbalanced openers,
                # we accept and continue iterating.
                old_unmatched = _count_unmatched_openers("\n".join(lines))
                new_unmatched = _count_unmatched_openers(candidate_code)
                if new_unmatched < old_unmatched:
                    logger.debug("SSR: change reduced unmatched openers; accepting provisional change and continuing.")
                    lines = candidate_lines
                    changed = True
                    break
                else:
                    # revert and try next opener
                    logger.debug("SSR: change did not reduce unmatched openers; reverting.")
                    continue

        if not changed:
            # If none of the single-opener attempts improved the unmatched count, try a combined conservative closure:
            combined = _close_all_openers_conservatively("\n".join(lines))
            if combined != "\n".join(lines) and _safe_parse(combined):
                logger.info("SSR: fixed by conservative all-opener closure.")
                return combined
            # else give up on further attempts
            break

    # Final attempt: try small aggressive close-all then syntax healers (but keep conservative)
    final_try = _close_all_openers_conservatively("\n".join(lines))
    if final_try != "\n".join(lines) and _safe_parse(final_try):
        logger.info("SSR: final conservative closure succeeded.")
        return final_try

    logger.warning("SSR: unable to fully repair; returning best-effort result.")
    return "\n".join(lines)


# ---------------------------
# Helper heuristics used above
# ---------------------------

def _count_unmatched_openers(code: str) -> int:
    """
    Count unmatched openers across the whole code (naive stack approach).
    Lower is better.
    """
    stack = []
    in_single = False
    in_double = False
    escaped = False
    for ch in code:
        if ch == "\\" and not escaped:
            escaped = True
            continue
        if ch == "'" and not escaped and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not escaped and not in_single:
            in_double = not in_double
            continue
        if in_single or in_double:
            escaped = False
            continue

        if ch in OPENERS:
            stack.append(OPENERS[ch])
        elif ch in OPENERS.values():
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                # unmatched closer - ignore
                pass
        escaped = False
    return len(stack)


def _close_all_openers_conservatively(code: str) -> str:
    """
    Append all unmatched closers to the end of the file in the reverse-order they were opened.
    Conservative but might fix many multiline literal cases.
    """
    stack = []
    in_single = False
    in_double = False
    escaped = False
    for ch in code:
        if ch == "\\" and not escaped:
            escaped = True
            continue
        if ch == "'" and not escaped and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not escaped and not in_single:
            in_double = not in_double
            continue
        if in_single or in_double:
            escaped = False
            continue

        if ch in OPENERS:
            stack.append(OPENERS[ch])
        elif ch in OPENERS.values():
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                # unmatched closer - ignore
                pass
        escaped = False

    if not stack:
        return code
    add = "".join(reversed(stack))
    logger.debug(f"SSR: conservative append of closers: {add}")
    # Append at end on its own line to avoid inline comment collisions
    return code.rstrip() + ("\n" if not code.endswith("\n") else "") + add + "\n"