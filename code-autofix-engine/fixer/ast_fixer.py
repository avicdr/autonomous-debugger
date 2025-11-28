"""
Ultra-Production-Mode AST Fixer V2
-----------------------------------

This module performs:
- aggressive syntax healing
- AST-based semantic repairs
- automatic import insertion
- name prefixing (math.sqrt)
- list/dict/tuple recovery
- incomplete expression recovery
- missing colon + indentation recovery
- unclosed strings/brackets
- missing commas
- incomplete call / trailing operator fix

Designed to succeed even on heavily corrupted Python code.
"""

from __future__ import annotations

import ast
import builtins
import logging
import re
from typing import Dict, Set, Tuple

from fixer.ast_rules import FUNC_TO_MODULE, PREFERRED_MODULES

logger = logging.getLogger(__name__)


# =============================================================================
#  PRIMARY ENTRYPOINT
# =============================================================================

def try_ast_fix(error_type: str, code: str) -> str:
    """
    Entrypoint for AST-based repair.

    Strategy:
    1. Try fast syntax fixes (brackets, quotes, colons, indentation, commas).
    2. Try aggressive AST healing.
    3. Then run semantic (import/name) fixes.
    """

    original = code

    # -----------------------------
    # SYNTAX FIXES FIRST
    # -----------------------------
    code = fix_unclosed_brackets(code)
    code = fix_backward_bracket_mismatch(code)
    code = fix_unclosed_strings(code)
    code = fix_missing_colons_and_indent(code)
    code = fix_missing_commas(code)
    code = fix_incomplete_calls(code)
    code = fix_broken_assignments(code)
    code = fix_trailing_operators(code)

    # Try parsing
    parsed = safe_parse(code)
    if parsed:
        logger.info("AST-V2: Syntax healed before semantic stage.")
        return fix_imports_and_names(code, parsed)

    # -----------------------------
    # AGGRESSIVE SYNTAX HEALER
    # -----------------------------
    code = heal_broken_expressions(code)
    parsed = safe_parse(code)

    if parsed:
        logger.info("AST-V2: Aggressive healing succeeded.")
        return fix_imports_and_names(code, parsed)

    # -----------------------------
    # FALLBACK: return modified code (may still be invalid)
    # -----------------------------
    logger.warning("AST-V2: Could not fully heal — returning best attempt.")
    return code or original


# =============================================================================
#  SAFE PARSE
# =============================================================================

def safe_parse(code: str):
    """
    Parse gracefully, return None if failing.
    """
    try:
        return ast.parse(code)
    except Exception:
        return None


# =============================================================================
#  BASIC SYNTAX HEALING
# =============================================================================

def fix_unclosed_brackets(code: str) -> str:
    """
    Add missing ')]}' to fix bracket mismatches.
    Handles nested stacks and mixed bracket usage.
    """
    stack = []
    BR = {"(": ")", "[": "]", "{": "}"}

    for ch in code:
        if ch in BR:
            stack.append(BR[ch])
        elif ch in BR.values():
            if stack and stack[-1] == ch:
                stack.pop()

    if stack:
        code += "".join(stack[::-1])

    return code


def fix_unclosed_strings(code: str) -> str:
    """
    Fix unbalanced quotes.
    """
    if code.count('"') % 2 == 1:
        code += '"'
    if code.count("'") % 2 == 1:
        code += "'"
    return code


def fix_missing_colons_and_indent(code: str) -> str:
    """
    Add missing ':' after def/if/for/while/class and fix indentation.
    """
    lines = code.split("\n")
    keywords = ("def ", "if ", "for ", "while ", "class ", "elif ", "else", "try", "except", "finally", "with ")

    out = []
    for i, line in enumerate(lines):
        s = line.strip()
        # missing colon
        if any(s.startswith(k) for k in keywords) and not s.endswith(":"):
            line = line.rstrip() + ":"

        out.append(line)

        # fix indentation for next line
        if line.strip().endswith(":") and i + 1 < len(lines):
            if lines[i + 1].strip() and not lines[i + 1].startswith(" "):
                lines[i + 1] = "    " + lines[i + 1]

    return "\n".join(out)


def fix_missing_commas(code: str) -> str:
    """
    Fix missing commas inside lists, tuples, dicts:
        [1 2 3] → [1, 2, 3]
    """
    def patch(m):
        return m.group(0).replace(" ", ", ")

    # Only patch inside bracket expressions
    return re.sub(r"\[(.*?)\]", lambda m: fix_list(m.group()), code)


def fix_list(text: str) -> str:
    """
    Repairs inside "[ ... ]"
    """
    inner = text[1:-1]
    tokens = re.split(r"\s+", inner)

    # If items look like literals, add commas
    if all(re.match(r"^[\w\(\)\+\-\*/]+$", t) for t in tokens):
        return "[" + ", ".join(tokens) + "]"
    return text


def fix_incomplete_calls(code: str) -> str:
    """
    Fix incomplete calls:
        print(  → print()
    """
    return re.sub(r"(\w+)\($", r"\1()", code)


def fix_broken_assignments(code: str) -> str:
    """
    Fix broken assignments like:
        x =
    """
    return re.sub(r"(\w+)\s*=\s*$", r"\1 = None", code)


def fix_trailing_operators(code: str) -> str:
    """
    Remove trailing operators: "1 +", "a *", "value and"
    """
    return re.sub(r"([+\-*/%]|and|or|==|!=)\s*$", "", code)


# =============================================================================
#  AGGRESSIVE EXPRESSION REPAIR
# =============================================================================

def heal_broken_expressions(code: str) -> str:
    """
    Fix malformed expressions by:
    - closing missing operators
    - adding parentheses
    - merging broken lines
    """
    lines = code.split("\n")
    repaired = []

    for line in lines:
        s = line.strip()

        # (1) Join lines ending with operator
        if re.search(r"[+\-*/%]$", s):
            line = line.rstrip(" +*/%-") + " 0"

        # (2) Fix empty list item like: [1, , 2]
        line = re.sub(r",\s*,", ", None,", line)

        # (3) Fix lone '('
        if s.endswith("("):
            line += ")"

        repaired.append(line if line.startswith((" ", "\t")) else line.lstrip())

    return "\n".join(repaired)


# =============================================================================
#  IMPORT + NAME REPAIR
# =============================================================================

def fix_imports_and_names(code: str, tree: ast.AST) -> str:
    """
    Perform:
    - missing import inference
    - name prefixing
    - from-import insertion
    - AST unparse
    """
    imported_modules, from_imports, defined_names = extract_defined(tree)
    used = collect_unresolved(tree, defined_names)

    add_imports = []
    prefix_map = {}

    for name in used:
        # not a builtin? try module mapping
        if name in FUNC_TO_MODULE:

            modules = PREFERRED_MODULES.get(name, [FUNC_TO_MODULE[name]])
            chosen = choose_best_module(modules, imported_modules, from_imports)

            if chosen in imported_modules:
                prefix_map[name] = chosen
            else:
                add_imports.append(f"from {chosen} import {name}")

    # Apply prefixing (math.sqrt)
    if prefix_map:
        tree = Prefixer(prefix_map).visit(tree)
        tree = ast.fix_missing_locations(tree)
        try:
            code = ast.unparse(tree)
        except Exception:
            pass

    # Insert missing imports
    if add_imports:
        code = insert_imports(code, add_imports)

    return code

def fix_backward_bracket_mismatch(code: str) -> str:
    """
    Ensures that extra closers ( ] ) } ) added by SSR or user mistakes
    do not break parsing. Removes unmatched closers.
    """
    stack = []
    result = []

    OPENERS = {"(": ")", "[": "]", "{": "}"}
    CLOSERS = {")": "(", "]": "[", "}": "{"}

    for ch in code:
        if ch in OPENERS:
            stack.append(ch)
            result.append(ch)
        elif ch in CLOSERS:
            if stack and stack[-1] == CLOSERS[ch]:
                stack.pop()
                result.append(ch)
            else:
                # skip unmatched closer
                continue
        else:
            result.append(ch)

    return "".join(result)


def extract_defined(tree: ast.AST):
    imported_modules = set()
    from_imports = {}
    defined = set(dir(builtins))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mod = a.name.split(".")[0]
                imported_modules.add(mod)
                defined.add(a.asname or mod)

        elif isinstance(node, ast.ImportFrom):
            mod = node.module.split(".")[0]
            imported_modules.add(mod)
            for a in node.names:
                from_imports.setdefault(mod, set()).add(a.name)
                defined.add(a.asname or a.name)

        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.add(node.name)

        elif isinstance(node, ast.arg):
            defined.add(node.arg)

        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defined.add(t.id)

    return imported_modules, from_imports, defined


def collect_unresolved(tree: ast.AST, defined: Set[str]):
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined:
                used.add(node.id)
    return used


def choose_best_module(candidates, imported_modules, from_imports):
    for c in candidates:
        if c.split(".")[0] in imported_modules:
            return c
    return candidates[0]


def insert_imports(code: str, new_imports: list[str]) -> str:
    lines = code.split("\n")

    # Find first non-comment, non-empty line
    idx = 0
    while idx < len(lines) and (lines[idx].strip() == "" or lines[idx].startswith("#")):
        idx += 1

    new_block = "\n".join(new_imports) + "\n"
    return "\n".join(lines[:idx] + [new_block] + lines[idx:])


class Prefixer(ast.NodeTransformer):
    def __init__(self, prefix_map):
        self.prefix_map = prefix_map

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id in self.prefix_map:
            return ast.copy_location(
                ast.Attribute(
                    value=ast.Name(id=self.prefix_map[node.id], ctx=ast.Load()),
                    attr=node.id,
                    ctx=ast.Load()
                ),
                node
            )
        return node
