# fixer/logical_detector_v2.py
"""
Logical Error Detector v2
-------------------------
Collection of static heuristics + lightweight dynamic testing to detect
silent logical bugs in Python code.

Entrypoint:
    inspect_and_test(code: str, timeout: float = 1.0) -> dict

Returned structure:
{
    "issues": [ {issue dict}, ... ],
    "tests": [ {test dict}, ... ],
    "test_results": [ {result dict}, ... ]
}

Issue dict fields:
{
    "issue_type": "FACTORIAL_BASE_CASE" | "RECURSION_NO_PROGRESS" | ...,
    "message": str,
    "location": (lineno, col_offset) or None,
    "evidence": str,
    "hint": str,
    "suggested_patch": { "kind": "text_replace", "pattern": "...", "replacement": "..." } (optional)
}
"""

from __future__ import annotations

import ast
import subprocess
import tempfile
import textwrap
import time
import json
import logging
import os
import re
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------------------------
# Utilities
# ---------------------------

def _safe_run_python(code_snippet: str, timeout: float = 1.0) -> Tuple[str, str, int]:
    """
    Execute small Python snippet in subprocess safely.
    Returns stdout, stderr, returncode.
    Uses `python -c` to avoid writing files when possible.
    """
    try:
        # Use system python executable
        cmd = [os.environ.get("PYTHON_EXECUTABLE", "python"), "-c", code_snippet]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    except Exception as e:
        return "", f"EXEC_ERROR: {e}", -2


def _ast_parse_safe(code: str) -> Optional[ast.AST]:
    try:
        return ast.parse(code)
    except Exception:
        return None


def _first_location(node: ast.AST) -> Optional[Tuple[int, int]]:
    if hasattr(node, "lineno") and hasattr(node, "col_offset"):
        return (getattr(node, "lineno"), getattr(node, "col_offset"))
    return None


# ---------------------------
# Heuristics (static AST)
# ---------------------------

def detect_factorial_base_case_heuristic(tree: ast.AST) -> List[Dict[str, Any]]:
    """
    Detect a function named 'factorial' that returns 0 for base case.
    """
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.lower() == "factorial":
            # search for return const 0
            for r in ast.walk(node):
                if isinstance(r, ast.Return) and isinstance(r.value, ast.Constant) and r.value.value == 0:
                    loc = _first_location(r)
                    issues.append({
                        "issue_type": "FACTORIAL_BASE_CASE",
                        "message": "factorial() returns 0 for base case; expected 1 for factorial(0).",
                        "location": loc,
                        "evidence": ast.get_source_segment(getattr(tree, "source", ""), r) or "return 0",
                        "hint": "Change base-case return to 1.",
                        "suggested_patch": {
                            "kind": "text_replace",
                            "pattern": r"return\s+0",
                            "replacement": "return 1"
                        }
                    })
    return issues


def detect_recursive_no_progress(tree: ast.AST, code: str) -> List[Dict[str, Any]]:
    """
    Detect recursion where recursive call uses same argument without arithmetic
    progress (no -1 or similar).
    """
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            # find any call nodes invoking func_name
            recursive_calls = []
            for call in [n for n in ast.walk(node) if isinstance(n, ast.Call)]:
                if isinstance(call.func, ast.Name) and call.func.id == func_name:
                    recursive_calls.append(call)

            if not recursive_calls:
                continue

            # check if any argument in recursive call indicates progress (BinOp with Sub)
            progress_found = False
            for call in recursive_calls:
                for arg in call.args:
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Sub, ast.Div, ast.FloorDiv)):
                        progress_found = True
                        break
                    # check for literal decrement: x-1 expressed as ast.UnaryOp? usually BinOp.
                if progress_found:
                    break

            if not progress_found:
                # conservatively ensure there is a base-case return that halts recursion
                has_base_case = False
                for ret in [n for n in ast.walk(node) if isinstance(n, ast.Return)]:
                    # detect comparisons like if n == 0: return ...
                    # look for Compare nodes in function body
                    if any(isinstance(n2, ast.Compare) for n2 in ast.walk(node)):
                        has_base_case = True
                        break
                loc = _first_location(node)
                issues.append({
                    "issue_type": "RECURSION_NO_PROGRESS",
                    "message": f"Function '{func_name}' appears recursive but no obvious progress toward base case detected.",
                    "location": loc,
                    "evidence": f"recursive calls: {len(recursive_calls)}; no decrement patterns found",
                    "hint": "Ensure recursive calls modify arguments toward the base case (e.g., n-1).",
                })
    return issues


def detect_mutable_default_args(tree: ast.AST) -> List[Dict[str, Any]]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg, default in zip(reversed(node.args.args), reversed(node.args.defaults)):
                # zip reversed aligns defaults with last args
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set, ast.Call)) or \
                   (isinstance(default, ast.Constant) and isinstance(default.value, (list, dict, set))):
                    loc = _first_location(default)
                    issues.append({
                        "issue_type": "MUTABLE_DEFAULT_ARG",
                        "message": "Function has mutable default argument which can lead to shared-state bugs.",
                        "location": loc,
                        "evidence": ast.get_source_segment(getattr(tree, "source", ""), default) or "mutable default",
                        "hint": "Use None as default and set inside function body."
                    })
    return issues


def detect_off_by_one_index_usage(tree: ast.AST, code: str) -> List[Dict[str, Any]]:
    """
    Heuristic: if code indexes x[i+1] inside a loop over range(len(x)) or range(n)
    this may be an off-by-one error.
    """
    issues = []
    for node in ast.walk(tree):
        # find subscript patterns
        if isinstance(node, ast.Subscript):
            # check for BinOp inside slice like a[i+1]
            if isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Add):
                # find enclosing loop (for)
                parent = getattr(node, "parent", None)
                # loosely detect: if there's a for loop above that iterates using range(len(...))
                cur = node
                found_for = None
                while cur:
                    cur = getattr(cur, "parent", None)
                    if isinstance(cur, ast.For):
                        found_for = cur
                        break
                if found_for:
                    loc = _first_location(node)
                    issues.append({
                        "issue_type": "OFF_BY_ONE_INDEX",
                        "message": "Possible off-by-one index usage (accessing i+1 inside loop over sequence).",
                        "location": loc,
                        "evidence": ast.get_source_segment(getattr(tree, "source", ""), node) or "subscript with +1",
                        "hint": "Check loop bounds and whether you might exceed sequence length."
                    })
    return issues


def detect_constant_index_out_of_range(tree: ast.AST, code: str) -> List[Dict[str, Any]]:
    """
    If there's a constant subscript arr[5] and arr is a literal list with fewer items,
    flag index out of range potential.
    """
    issues = []
    # map variable to literal list length when assignment like arr = [1,2,3]
    literal_lengths = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    literal_lengths[name] = len(node.value.elts)
    # detect const subscripts
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                idx = node.slice.value
                if isinstance(node.value, ast.Name) and node.value.id in literal_lengths:
                    ln = literal_lengths[node.value.id]
                    if idx >= ln or idx < -ln:
                        loc = _first_location(node)
                        issues.append({
                            "issue_type": "POTENTIAL_INDEX_OUT_OF_RANGE",
                            "message": f"Index {idx} on literal '{node.value.id}' of length {ln} will be out of range.",
                            "location": loc,
                            "evidence": f"{node.value.id}[{idx}]",
                            "hint": f"Use a valid index (< {ln}) or guard access with bounds check."
                        })
    return issues


def detect_always_true_false_conditions(tree: ast.AST) -> List[Dict[str, Any]]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # check for Compare node with constant true/false or identity misuse
            for comp in [n for n in ast.walk(node.test) if isinstance(n, ast.Compare)]:
                for c in comp.comparators:
                    if isinstance(c, ast.Constant) and isinstance(c.value, bool):
                        loc = _first_location(comp)
                        issues.append({
                            "issue_type": "SUSPICIOUS_BOOLEAN_COMPARE",
                            "message": "Suspicious boolean comparison (comparison to True/False).",
                            "location": loc,
                            "evidence": ast.get_source_segment(getattr(tree, "source", ""), comp) or "compare to bool",
                            "hint": "Prefer direct truthiness checks (if x:) or use '==' only when intended."
                        })
    return issues


def detect_shadowing_builtins(tree: ast.AST) -> List[Dict[str, Any]]:
    shadow_issues = []
    builtins_set = set(dir(__builtins__))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in builtins_set:
                    loc = _first_location(t)
                    shadow_issues.append({
                        "issue_type": "SHADOW_BUILTIN",
                        "message": f"Assignment shadows builtin '{t.id}'.",
                        "location": loc,
                        "evidence": t.id,
                        "hint": "Rename variable to avoid shadowing builtins."
                    })
    return shadow_issues


def detect_unreachable_code(tree: ast.AST) -> List[Dict[str, Any]]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            for i, stmt in enumerate(body[:-1]):
                if isinstance(stmt, ast.Return):
                    # anything after a return in the same block is unreachable
                    next_stmt = body[i + 1]
                    loc = _first_location(next_stmt)
                    issues.append({
                        "issue_type": "UNREACHABLE_CODE",
                        "message": "Code after return statement in a function is unreachable.",
                        "location": loc,
                        "evidence": ast.get_source_segment(getattr(tree, "source", ""), next_stmt) or "<stmt>",
                        "hint": "Remove unreachable code or move it before the return."
                    })
    return issues


# Aggregate static detectors
STATIC_DETECTORS = [
    detect_factorial_base_case_heuristic,
    detect_recursive_no_progress,
    detect_mutable_default_args,
    detect_off_by_one_index_usage,
    detect_constant_index_out_of_range,
    detect_always_true_false_conditions,
    detect_shadowing_builtins,
    detect_unreachable_code,
]


# ---------------------------
# Test generation heuristics
# ---------------------------

def _generate_basic_tests_for_function(func_node: ast.FunctionDef) -> List[Dict[str, Any]]:
    """
    Generate simple tests for some recognized function names/patterns.
    Output test dict:
      { "call": "factorial(5)", "expected": "120", "expect_stdout": False, "description": "..."}
    """
    name = func_node.name.lower()
    tests = []
    if name == "factorial":
        tests = [
            {"call": f"{func_node.name}(0)", "expected": "1", "description": "factorial base case"},
            {"call": f"{func_node.name}(1)", "expected": "1", "description": "factorial 1"},
            {"call": f"{func_node.name}(5)", "expected": "120", "description": "factorial 5"},
        ]
    elif name in {"fib", "fibonacci"}:
        tests = [
            {"call": f"{func_node.name}(0)", "expected": "0", "description": "fib 0"},
            {"call": f"{func_node.name}(1)", "expected": "1", "description": "fib 1"},
            {"call": f"{func_node.name}(6)", "expected": "8", "description": "fib 6"},
        ]
    elif name in {"sum_list", "sumarr", "sumarray", "sum"}:
        tests = [
            {"call": f"{func_node.name}([1,2,3])", "expected": "6", "description": "sum of list"},
        ]
    elif name in {"is_palindrome", "ispalindrome"}:
        tests = [
            {"call": f"{func_node.name}('a')", "expected": "True", "description": "palindrome single char"},
            {"call": f"{func_node.name}('aba')", "expected": "True", "description": "palindrome 'aba'"},
            {"call": f"{func_node.name}('ab')", "expected": "False", "description": "not palindrome"},
        ]
    elif name in {"max_in_list", "maxlist", "max"}:
        tests = [
            {"call": f"{func_node.name}([1,5,3])", "expected": "5", "description": "max of list"},
        ]
    # Add more heuristics as needed
    return tests


def generate_tests(code: str) -> List[Dict[str, Any]]:
    """
    Inspect AST for function definitions and generate small tests.
    """
    tests = []
    tree = _ast_parse_safe(code)
    if tree is None:
        return tests

    # attach source to tree to help detectors (for evidence)
    setattr(tree, "source", code)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            func_tests = _generate_basic_tests_for_function(node)
            for t in func_tests:
                tests.append({
                    "function": node.name,
                    "call": t["call"],
                    "expected": t["expected"],
                    "description": t["description"]
                })
    return tests


def detect_known_patterns(code: str):
    issues = []

    if "preorder(" in code and "res.append" in code:
        if ("preorder(root.left" in code and 
            "res.append(root.val)" in code):
            # Looks like in-order but named preorder
            issues.append({
                "problem": "Wrong traversal order: function name is preorder but logic is inorder",
                "suggested_patch": None
            })

    if "return memo[0]" in code:
        issues.append({
            "problem": "Memoization bug: returning wrong key",
            "suggested_patch": {
                "kind": "text_replace",
                "pattern": r"memo\[0\]",
                "replacement": "memo[n]"
            }
        })

    return issues


# ---------------------------
# Running tests dynamically
# ---------------------------

def _build_test_driver(code: str, tests: List[Dict[str, Any]]) -> str:
    """
    Build a python -c driver that imports/defines the code and runs tests,
    printing JSON of results to stdout.
    """
    # The safe approach: create a script that defines functions from `code` (by pasting)
    # then runs each test and prints JSON result
    wrapper = []
    # protect against prints in user code by redirecting stdout inside individual tests
    wrapper.append("import json, sys, traceback")
    wrapper.append("results = []")
    wrapper.append("def _run_test(fn_call):")
    wrapper.append("    try:")
    wrapper.append("        # eval the call and stringify result")
    wrapper.append("        val = eval(fn_call, globals())")
    wrapper.append("        return {'ok': True, 'result': repr(val), 'error': None}")
    wrapper.append("    except Exception as e:")
    wrapper.append("        tb = traceback.format_exc()")
    wrapper.append("        return {'ok': False, 'result': None, 'error': tb}")
    wrapper.append("")
    # inject user code
    # ensure no encoding issues
    wrapper.append("# --- Begin user code ---")
    for line in code.splitlines():
        wrapper.append(line)
    wrapper.append("# --- End user code ---")
    wrapper.append("")
    # add tests
    wrapper.append("try:")
    wrapper.append("    tests = []")
    for t in tests:
        call = t["call"].replace('"', r'\"')
        wrapper.append(f"    tests.append({json.dumps(t)})")
    wrapper.append("    for t in tests:")
    wrapper.append("        res = _run_test(t['call'])")
    wrapper.append("        out = {'call': t['call'], 'expected': t['expected'], 'ok': res['ok'], 'result': res['result'], 'error': res['error'], 'description': t.get('description')}")
    wrapper.append("        results.append(out)")
    wrapper.append("except Exception as e:")
    wrapper.append("    results.append({'call': None, 'expected': None, 'ok': False, 'result': None, 'error': str(e)})")
    wrapper.append("print(json.dumps(results))")
    driver = "\n".join(wrapper)
    return driver


def run_tests_in_subprocess(code: str, tests: List[Dict[str, Any]], timeout: float = 1.0) -> List[Dict[str, Any]]:
    """
    Runs the generated tests in a subprocess and returns parsed JSON results.
    """
    if not tests:
        return []
    driver = _build_test_driver(code, tests)
    stdout, stderr, rc = _safe_run_python(driver, timeout=timeout)
    if stderr and stderr != "TIMEOUT" and not stdout:
        # execution failed before tests (syntax/runtime in import)
        logger.debug("run_tests_in_subprocess: pre-test failure", extra={"stderr": stderr})
    results = []
    if stdout:
        try:
            results = json.loads(stdout)
        except Exception:
            # try fallback: sometimes extra prints appear; extract JSON substring
            m = re.search(r"(\[.*\])", stdout, re.S)
            if m:
                try:
                    results = json.loads(m.group(1))
                except Exception:
                    results = []
    # If timed out
    if stderr == "TIMEOUT":
        return [{"call": None, "expected": None, "ok": False, "result": None, "error": "TIMEOUT"}]
    return results


# ---------------------------
# Synthesis: analyze test results and propose hints
# ---------------------------

def analyze_test_results(tests: List[Dict[str, Any]], results: List[Dict[str, Any]], code: str) -> List[Dict[str, Any]]:
    """
    For failing tests, produce issue objects with hints and safe small patches if possible.
    """
    issues = []
    tree = _ast_parse_safe(code)
    if tree is None:
        return issues

    for t, r in zip(tests, results):
        if not r.get("ok"):
            # failing test → create issue
            call = t["call"]
            desc = t.get("description", "")
            # Heuristics for known patterns (factorial)
            if re.match(r".*factorial\(", call):
                # search for "return 0" in factorial function
                if re.search(r"def\s+factorial\s*\(", code):
                    m = re.search(r"(def\s+factorial\s*\(.*?\):)([\s\S]*?)(?=def\s|\Z)", code)
                    if m:
                        body = m.group(2)
                        if re.search(r"return\s+0\b", body):
                            issues.append({
                                "issue_type": "TEST_FAILURE_FACTORIAL_BASE",
                                "message": f"factorial function fails test '{desc}'.",
                                "location": _first_location(maybe_node_from_name(tree, "factorial")),
                                "evidence": f"test call: {call}, error: {r.get('error')}",
                                "hint": "Change factorial base-case to return 1.",
                                "suggested_patch": {
                                    "kind": "text_replace",
                                    "pattern": r"(def\s+factorial\s*\(.*?\):)([\s\S]*?)return\s+0\b",
                                    "replacement": r"\1\2return 1"
                                }
                            })
                            continue
            # Generic failing test issue
            issues.append({
                "issue_type": "TEST_FAILURE",
                "message": f"Test '{desc}' for call {call} failed.",
                "location": None,
                "evidence": f"error: {r.get('error')}",
                "hint": "Inspect function logic or run test locally with prints."
            })
    return issues


def maybe_node_from_name(tree: ast.AST, name: str) -> Optional[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


# ---------------------------
# High-level inspector
# ---------------------------

def inspect_and_test(code: str, timeout: float = 1.0) -> Dict[str, Any]:
    """
    Enhanced logical detector:
      - instant pattern-based logical detection for known bugs
      - static AST analysis
      - dynamic test generation + execution
    """
    result = {
        "issues": [],
        "tests": [],
        "test_results": []
    }

    tree = _ast_parse_safe(code)
    if tree is not None:
        setattr(tree, "source", code)

    # ---------------------------------------------------------
    # 1. FAST KNOWN-BUG STATIC PATTERN DETECTION (NEW)
    # ---------------------------------------------------------
    fast_issues = detect_known_patterns(code)
    if fast_issues:
        # These are always high-confidence → return immediately
        result["issues"].extend(fast_issues)
        result["note"] = "Known logical pattern detected (fast)."
        return result

    # ---------------------------------------------------------
    # 2. STATIC ANALYSIS USING REGISTERED DETECTORS
    # ---------------------------------------------------------
    if tree is not None:
        static_issues = []
        for detector in STATIC_DETECTORS:
            try:
                if detector.__code__.co_argcount == 2:
                    issues = detector(tree, code)
                else:
                    issues = detector(tree)

                if issues:
                    static_issues.extend(issues)

            except Exception as e:
                logger.debug(f"Static detector {detector.__name__} raised: {e}")

        result["issues"].extend(static_issues)

        # If static detectors already found issues → skip dynamic tests
        if static_issues:
            result["note"] = "Static logical issues detected."
            return result

    # ---------------------------------------------------------
    # 3. TEST GENERATION
    # ---------------------------------------------------------
    tests = generate_tests(code)
    result["tests"] = tests

    if not tests:
        result["note"] = "No tests generated. No static issues found."
        return result

    # ---------------------------------------------------------
    # 4. DYNAMIC TEST EXECUTION
    # ---------------------------------------------------------
    start = time.time()
    test_results = run_tests_in_subprocess(code, tests, timeout=timeout)
    elapsed = time.time() - start

    logger.debug(f"run_tests_in_subprocess finished in {elapsed:.3f}s")
    result["test_results"] = test_results

    # ---------------------------------------------------------
    # 5. DYNAMIC RESULT ANALYSIS
    # ---------------------------------------------------------
    dyn_issues = analyze_test_results(tests, test_results, code)
    result["issues"].extend(dyn_issues)

    if dyn_issues:
        result["note"] = "Dynamic tests identified logical issues."
        return result

    # ---------------------------------------------------------
    # 6. NO ISSUES FOUND (STATIC + DYNAMIC)
    # ---------------------------------------------------------
    result["note"] = (
        "No logical issues detected statically or dynamically. "
        "This does NOT guarantee correctness."
    )

    return result


def _apply_suggested_patches(code: str, issues: list) -> str:
    """
    Safe small regex-based patch applier used by iteration controller.
    Delegates to suggested_patch instructions in issues (if any).
    """
    import re
    patched = code
    for issue in issues:
        patch = issue.get("suggested_patch")
        if not patch:
            continue
        if patch.get("kind") == "text_replace":
            try:
                new = re.sub(patch["pattern"], patch["replacement"], patched)
                if new != patched:
                    patched = new
            except Exception:
                continue
    return patched


# ---------------------------
# quick CLI for local debugging
# ---------------------------

if __name__ == "__main__":
    import argparse, sys
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", help="python file to inspect")
    p.add_argument("--timeout", type=float, default=1.0)
    args = p.parse_args()
    code = ""
    if args.path:
        with open(args.path, "r", encoding="utf-8") as f:
            code = f.read()
    else:
        code = sys.stdin.read()
    out = inspect_and_test(code, timeout=args.timeout)
    print(json.dumps(out, indent=2))
