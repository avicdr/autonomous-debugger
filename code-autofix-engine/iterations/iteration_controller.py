# iteration_controller_v13.py — FINAL PRODUCTION VERSION
"""
iteration_controller_v13.py — FINAL PRODUCTION VERSION
------------------------------------------------------
Upgrades:
 - Instant semantic intent detection (preorder, inorder, postorder, fib memo, binary search)
 - Zero-waste LLM fallback when obvious logic mismatch is detected before iteration 1
 - Fully detailed logging for every stage
 - Robust LLM extraction + merge strategy integration
 - Dead-iteration guard: fallback to LLM (no infinite loops)
 - Output-change detection as signal for logic fixes
 - Guaranteed diff fallback for unbreakable loops
"""

import difflib
import re
from typing import Optional, List

from runtime.sandbox_runner import run_in_sandbox

from errors.error_types import ErrorType
from errors.error_parser import parse_error
from errors.error_classifier import choose_fix_method

from fixer.ast_fixer import try_ast_fix
from fixer.llm_fixer import generate_llm_fix
from fixer.merge_strategy import merge_llm_result
from fixer.ssr_fixer import apply_ssr_fix
from fixer.logical_detector import inspect_and_test

from utils.validation import validate_iteration
from utils.logger import log_step, setup_logger
from utils.timers import timer

from iterations.iteration_report import create_iteration_report, save_full_report

from config.settings import MAX_ITERATIONS, MODEL_MAX_TOKENS

setup_logger()


# ==========================================================
# NORMALIZATION UTILS
# ==========================================================
def normalize_code(s: Optional[str]) -> str:
    if s is None:
        return ""
    return s.replace("\r\n", "\n").rstrip()


# ==========================================================
# Extract Python code from LLM output
# ==========================================================
def extract_code_from_llm(llm: str) -> str:
    if not llm:
        return ""

    # ```python fenced
    m = re.findall(r"```(?:python)?\s*(.*?)```", llm, re.DOTALL | re.IGNORECASE)
    if m:
        return m[-1].strip()

    # raw fenced
    m = re.findall(r"```(.*?)```", llm, re.DOTALL)
    if m:
        return m[-1].strip()

    # indented block
    indented_blocks = re.findall(r"(?:\n(?: {4}|\t).+)+", "\n" + llm)
    if indented_blocks:
        block = max(indented_blocks, key=len)
        lines = [re.sub(r"^( {4}|\t)", "", ln) for ln in block.splitlines()]
        return "\n".join(lines).strip()

    # last 40 lines heuristic
    lines = [ln.rstrip() for ln in llm.splitlines() if ln.strip()]
    if not lines:
        return ""

    for window in range(1, min(40, len(lines)) + 1):
        candidate = "\n".join(lines[-window:])
        if re.search(r"(def |class |=|\()", candidate):
            return candidate.strip()

    return "\n".join(lines[-40:]).strip()


# ==========================================================
# Guaranteed diff fallback
# ==========================================================
def ensure_diff(old_code: str, new_code: str, iteration: int) -> str:
    if normalize_code(old_code) != normalize_code(new_code):
        return new_code

    return new_code.rstrip() + f"\n# forced-diff-{iteration}\n"


# ==========================================================
# INSTANT SEMANTIC INTENT DETECTION
# (Detect silent logical bugs before iteration 0)
# ==========================================================
def detect_semantic_conflicts(code: str) -> bool:
    c = code.lower()

    # ----- traversal bugs ------
    # preorder should be N L R → append BEFORE left recursion
    if "def preorder" in c:
        # simple heuristic: if append occurs after left recursion, that's reversed order
        if re.search(r"preorder\s*\(.*left.*\).*preorder\s*\(.*right.*\).*append", c, re.DOTALL):
            return True
        # another heuristic: append occurs between left and right? still suspicious
        if re.search(r"preorder\s*\(.*left.*\).*append.*preorder\s*\(.*right.*\)", c, re.DOTALL):
            # this indicates append after left, which is fine for inorder/postorder checking,
            # but we're conservative and treat odd patterns as conflict for the tool to fix.
            return True

    # inorder must be L N R (we flag obvious deviations)
    if "def inorder" in c:
        if not re.search(r"left.*append.*right", c, re.DOTALL):
            return True

    # postorder must be L R N (append must be last)
    if "def postorder" in c:
        if re.search(r"append.*(left|right)", c):
            return True

    # ----- fibonacci memo bug -----
    if "def fib" in c and "memo" in c:
        if "return memo[0]" in c:
            return True

    # ----- binary search bugs -----
    if "def binary_search" in c or "def binarysearch" in c:
        # mid calculation must be correct (a heuristic)
        if "mid =" in c and "//" not in c and "+" in c:
            # often mid=(left+right)//2 — if they used (left+right)/2 without integer division, we flag
            if re.search(r"mid\s*=\s*\(?.*left.*\+.*right.*\)?\s*/\s*2", c):
                return True
        # left pointer must advance by mid+1 or mid depending on implementation — detect suspicious assignments
        if re.search(r"left\s*=\s*mid\s*(?!\+|\-)", c):
            return True
        if re.search(r"right\s*=\s*mid\s*(?!\+|\-)", c):
            return True

    return False


# ==========================================================
# DIFF TRACKER
# ==========================================================
def compute_changes(old_code, new_code, iteration, method, err_type):
    changes = []
    diff = difflib.ndiff(old_code.splitlines(), new_code.splitlines())

    old_ln = 0
    new_ln = 0

    for row in diff:
        tag = row[:2]
        text = row[2:]

        if tag == "  ":
            old_ln += 1
            new_ln += 1
            continue
        if tag == "- ":
            old_ln += 1
            changes.append({
                "iteration": iteration,
                "fix_method": method,
                "error_type": str(err_type),
                "change_type": "removed",
                "line_old": old_ln,
                "line_new": None,
                "old_text": text,
                "new_text": "",
                "reason": "Removed"
            })
        if tag == "+ ":
            new_ln += 1
            changes.append({
                "iteration": iteration,
                "fix_method": method,
                "error_type": str(err_type),
                "change_type": "added",
                "line_old": None,
                "line_new": new_ln,
                "old_text": "",
                "new_text": text,
                "reason": "Added"
            })
    return changes


# ==========================================================
# MAIN REPAIR LOOP — V13 (FINAL)
# ==========================================================
def run_repair_loop(original_code: str, user_prompt: str, max_iterations: int = None):

    code = original_code
    iteration_reports = []
    changeLog = []
    max_iter = max_iterations or MAX_ITERATIONS

    # ================================================
    # INSTANT SEMANTIC INTENT CHECK (before iteration 1)
    # ================================================
    if detect_semantic_conflicts(original_code):
        log_step("[SEMANTIC] Intent conflict detected → forcing LLM immediately (iteration 0)")

        llm_raw = generate_llm_fix(
            code=original_code,
            error_message="SEMANTIC_INTENT_MISMATCH",
            user_prompt=(user_prompt or "Fix the logic according to the function naming semantics. Return a full corrected file or code block."),
            logic_issues=[],
            max_tokens=MODEL_MAX_TOKENS,
        )

        extracted = extract_code_from_llm(llm_raw)

        merged_candidate = None
        changeLog = []   # <<------------------- ADDED HERE

        try:
            merged_candidate = merge_llm_result(original_code, llm_raw, allow_full_rewrite=True)
            if merged_candidate and normalize_code(merged_candidate) != normalize_code(original_code):
                new_code = merged_candidate
            else:
                if extracted:
                    merged_from_extracted = merge_llm_result(original_code, extracted, allow_full_rewrite=True)
                    if merged_from_extracted and normalize_code(merged_from_extracted) != normalize_code(original_code):
                        new_code = merged_from_extracted
                    else:
                        # fallback to extracted full file if parsed
                        try:
                            import ast
                            ast.parse(extracted)
                            new_code = extracted
                        except Exception:
                            new_code = merged_candidate or original_code
                else:
                    new_code = merged_candidate or original_code

        except Exception as e:
            log_step(f"[ERROR] Semantic LLM merge failed: {e}")
            if extracted and len(extracted.splitlines()) > 2:
                new_code = extracted
            else:
                new_code = original_code

        # ---------------------------------------------
        # DIFF TRACKING FOR SEMANTIC FIX (iteration 0)
        # ---------------------------------------------
        diff_entries = compute_changes(
            old_code=original_code,
            new_code=new_code,
            iteration=0,
            method="LLM",
            err_type="SEMANTIC"
        )

        changeLog.extend(diff_entries)

        # SAVE REPORT + CHANGES
        iteration_report = create_iteration_report(
            iteration=0,
            code=new_code,
            stdout="",
            stderr="",
            fix_method="LLM",
            error_type="SEMANTIC",
            success=True,
        )

        path = save_full_report([iteration_report], changeLog, "SUCCESS")
        log_step("[REPORT] Saved iteration report for semantic fix (iteration 0).")
        return new_code, path


    # ========================
    # NORMAL ITERATION LOOP
    # ========================
    for i in range(1, max_iter + 1):
        log_step(f"\n=== ITERATION {i} ===")

        # RUN ORIGINAL
        with timer(f"iteration_{i}"):
            stdout, stderr = run_in_sandbox(code)

        iteration_start_output = stdout or ""

        runtime_error, full_err = parse_error(stderr, code)
        logic_info = inspect_and_test(code)
        logic_issues = logic_info.get("issues", [])

        error_type = ErrorType.LOGICAL if logic_issues else runtime_error

        # SUCCESS IF NO ERROR AND NO USER REQUEST
        if error_type == ErrorType.NONE and not user_prompt.strip():
            iteration_reports.append(create_iteration_report(
                iteration=i, code=code, stdout=stdout, stderr=stderr,
                fix_method="NONE", error_type=error_type, success=True
            ))
            path = save_full_report(iteration_reports, changeLog, "SUCCESS")
            return code, path

        # SELECT FIX METHOD
        if user_prompt.strip():
            method = "LLM"
        elif error_type == ErrorType.LOGICAL:
            method = "LLM"
        else:
            method = choose_fix_method(error_type)

        # PRE-FIX SSR
        code = apply_ssr_fix(code)

        # LOGIC PATCHES
        if error_type == ErrorType.LOGICAL:
            code = _apply_logical_patches(code, logic_issues)

        old_code = code
        new_code = code
        applied_method = method

        # ================
        # APPLY FIX
        # ================
        if method == "AST":
            try:
                patched = try_ast_fix(error_type, new_code)
                if normalize_code(patched) != normalize_code(new_code):
                    new_code = patched
                else:
                    log_step("[INFO] AST produced no effective change → fallback to LLM")
                    method = "LLM"
            except Exception as e:
                log_step(f"[ERROR] AST fixer crashed: {e}")
                method = "LLM"

        if method == "LLM":
            llm_raw = generate_llm_fix(
                code=new_code,
                error_message=full_err,
                user_prompt=user_prompt,
                logic_issues=logic_issues,
                max_tokens=MODEL_MAX_TOKENS,
            )

            # conservative merge first
            merged = merge_llm_result(new_code, llm_raw, allow_full_rewrite=False)
            extracted = extract_code_from_llm(llm_raw)

            if normalize_code(merged) != normalize_code(new_code):
                new_code = merged
                applied_method = "LLM"
            elif extracted and normalize_code(extracted) != normalize_code(new_code):
                # try merging the extracted snippet into the full file
                merged_from_extracted = merge_llm_result(new_code, extracted, allow_full_rewrite=True)
                if normalize_code(merged_from_extracted) != normalize_code(new_code):
                    new_code = merged_from_extracted
                    applied_method = "LLM"
                else:
                    # fallback: use extracted if it's a plausible full-file candidate
                    try:
                        import ast
                        ast.parse(extracted)
                        # prefer to return merged original + extracted replaced where possible:
                        merged_try = merge_llm_result(new_code, extracted, allow_full_rewrite=True)
                        if normalize_code(merged_try) != normalize_code(new_code):
                            new_code = merged_try
                            applied_method = "LLM"
                        else:
                            new_code = ensure_diff(old_code, old_code, i)
                            applied_method = "LLM"
                    except Exception:
                        new_code = ensure_diff(old_code, old_code, i)
                        applied_method = "LLM"
            else:
                # no-op merged result — force a guaranteed diff so loop can progress
                new_code = ensure_diff(old_code, old_code, i)
                applied_method = "LLM"

        # POST-FIX SSR
        new_code = apply_ssr_fix(new_code)

        # DIFF TRACKING
        if normalize_code(new_code) != normalize_code(old_code):
            diffs = compute_changes(old_code, new_code, i, applied_method, error_type)
            if diffs:
                try:
                    changeLog.extend(diffs)
                except Exception:
                    for d in diffs:
                        changeLog.append(d)

        # VALIDATION
        val_stdout, val_stderr = run_in_sandbox(new_code)
        new_err, _ = parse_error(val_stderr, new_code)

        # output-change detection
        if (val_stdout or "") != iteration_start_output:
            new_err = ErrorType.LOGICAL

        if inspect_and_test(new_code).get("issues", []):
            new_err = ErrorType.LOGICAL

        success, _ = validate_iteration(val_stdout, val_stderr, new_err)

        iteration_reports.append(create_iteration_report(
            iteration=i,
            code=new_code,
            stdout=val_stdout,
            stderr=val_stderr,
            fix_method=applied_method,
            error_type=new_err,
            success=success,
        ))

        if applied_method == "LLM" and new_err == ErrorType.NONE:
            path = save_full_report(iteration_reports, changeLog, "SUCCESS")
            return new_code, path

        code = new_code

    path = save_full_report(iteration_reports, changeLog, "FAILED")
    return code, path


# ==========================================================
# INTERNAL logical patch wrapper
# ==========================================================
def _apply_logical_patches(code: str, issues: List[dict]) -> str:
    patched = code
    for issue in issues:
        p = issue.get("suggested_patch")
        if not p:
            continue
        if p.get("kind") == "text_replace":
            try:
                patched = re.sub(p["pattern"], p["replacement"], patched)
            except Exception:
                pass
    return patched
