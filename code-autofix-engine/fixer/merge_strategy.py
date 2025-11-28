# fixer/merge_strategy.py
"""
Robust merge strategy with hybrid patching + full-function-rewrite fallback.

API:
    merge_llm_result(base: str, llm_out: str, allow_full_rewrite: bool = False) -> str

Behavior:
- If LLM output contains a clean-parsing candidate that is not a massive shrink/expansion, adopt it.
- If candidate parses but would shrink the file massively, reject it (return base).
- If candidate doesn't parse, attempt region-preserving merge:
    * Replace top-level function/class definitions from candidate (if individually parsable).
- If partial merge produced no effective change and allow_full_rewrite==True:
    * Attempt to extract function definitions from candidate and replace the corresponding full function bodies
      in base (function-level rewrite). Accept only if merged parses and doesn't hallucinate too much.
- If everything fails, return base unchanged.
- Conservative hallucination thresholds are configurable below.
"""

from __future__ import annotations
import ast
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# --- Tunables ---
MAX_ADDED_TOPLEVEL_DEFS = 12
MAX_ADDED_IMPORTS = 8
SHRINK_THRESHOLD = 0.75  # candidate lines must be at least 75% of base lines to be accepted
MAX_NEW_TOPLEVEL_IF_HUGE = 6  # if file huge, be stricter on new defs

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _parse_ok(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except Exception:
        return False

def _safe_parse_tree(code: str) -> Optional[ast.Module]:
    try:
        return ast.parse(code)
    except Exception:
        return None

def _top_level_names(code: str) -> List[str]:
    tree = _safe_parse_tree(code)
    if not tree:
        return []
    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
    return names

def _imports_from_code(code: str) -> List[str]:
    tree = _safe_parse_tree(code)
    if not tree:
        return []
    imps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imps.append(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imps.append(node.module.split(".")[0])
    return imps

def _strip_non_code_prefix(s: str) -> str:
    """
    Remove any leading human-readable text / instructions LLM might add
    before the first python-like line.
    """
    lines = s.splitlines()
    for i, ln in enumerate(lines[:40]):
        if re.match(r'^\s*(def |class |import |from |[A-Za-z_]\w*\s*=|if |for |while |async def )', ln):
            return "\n".join(lines[i:])
    # if nothing matched, return original
    return s

def _count_lines(s: str) -> int:
    if not s:
        return 0
    return len(s.splitlines())

def _get_source_segment_for_node(code: str, node: ast.AST) -> Optional[str]:
    """
    Attempt to get the exact source segment for a top-level node.
    Uses ast.get_source_segment when available; otherwise fall back to regex heuristic.
    """
    try:
        # ast.get_source_segment available in Python 3.8+ when original source provided
        segment = ast.get_source_segment(code, node)
        if segment:
            return segment
    except Exception:
        pass

    # Fallback: simple regex for def/class capture (approximate)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        name = node.name
        pattern = rf"(?:^|\n)(?:async\s+def|def|class)\s+{re.escape(name)}\b[^\n]*:\n(?:\s+.*\n)+"
        m = re.search(pattern, code)
        if m:
            return m.group(0)
    return None

def _safe_replace_first(target: str, pattern: str, replacement: str) -> str:
    return re.sub(pattern, replacement, target, count=1, flags=re.MULTILINE)

# ---------------------------------------------------------------------------
# Merge strategy implementation
# ---------------------------------------------------------------------------

def merge_llm_result(base: str, llm_out: str, allow_full_rewrite: bool = False) -> str:
    """
    Merge LLM output into base code.

    Parameters:
    - base: original file content
    - llm_out: raw LLM text
    - allow_full_rewrite: if True, attempt function-level full rewrite fallback when minimal merges fail

    Returns merged_code (or base if rejected).
    """
    if not llm_out:
        return base

    candidate = _strip_non_code_prefix(llm_out).strip()
    # quick normalization
    base_lines = _count_lines(base)
    cand_lines = _count_lines(candidate)

    # --- 1) If candidate parses fully, apply high-level heuristics (accept/reject) ---
    if _parse_ok(candidate):
        # Hallucination checks
        base_names = set(_top_level_names(base))
        cand_names = set(_top_level_names(candidate))
        added_defs = cand_names - base_names

        base_imports = set(_imports_from_code(base))
        cand_imports = set(_imports_from_code(candidate))
        new_imports = cand_imports - base_imports

        # Reject if candidate shrinks file massively (protect against truncation)
        if base_lines > 0 and cand_lines < max(1, int(base_lines * SHRINK_THRESHOLD)):
            logger.warning("merge_llm_result: rejecting candidate because it would massively shrink the file")
            # don't accept shrink — avoid losing content
            # (caller may then try other strategies or full-rewrite with allow_full_rewrite)
            return base

        # Reject if too many brand-new top-level defs / imports (likely hallucination)
        if len(added_defs) > MAX_ADDED_TOPLEVEL_DEFS or len(new_imports) > MAX_ADDED_IMPORTS:
            logger.warning("merge_llm_result: rejecting candidate due to excessive top-level additions (possible hallucination)")
            return base

        # Otherwise accept candidate as-is
        logger.info("merge_llm_result: adopting llm candidate (parsed OK and passed heuristics)")
        return candidate

    # --- 2) Candidate doesn't parse: attempt region-preserving partial merge ---
    try:
        base_tree = ast.parse(base)
    except Exception:
        logger.debug("merge_llm_result: base does not parse; refusing to merge / returning base")
        return base

    merged = base
    cand_tree = _safe_parse_tree(candidate)
    if cand_tree:
        # Replace full top-level defs (func/class) from candidate if we can extract their source and they parse in isolation
        replaced_any = False
        for node in cand_tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                src_node = _get_source_segment_for_node(candidate, node)
                if not src_node:
                    continue
                # validate extracted node in isolation
                try:
                    _ = ast.parse(src_node)
                except Exception:
                    # not a valid isolated node
                    continue
                # try to find existing definition in base
                name = node.name
                pattern = rf"(?:^|\n)(?:async\s+def|def|class)\s+{re.escape(name)}\b[^\n]*:\n(?:\s+.*\n)+"
                if re.search(pattern, merged, flags=re.MULTILINE):
                    # replace the first occurrence
                    merged_candidate = _safe_replace_first(merged, pattern, "\n" + src_node + "\n")
                    if _parse_ok(merged_candidate):
                        merged = merged_candidate
                        replaced_any = True
                        logger.info(f"merge_llm_result: replaced definition '{name}' from candidate")
                    else:
                        # try a more conservative inline replace: replace whole def region via AST extraction
                        # (skip if it fails)
                        pass

        if replaced_any and _parse_ok(merged):
            logger.info("merge_llm_result: partial merge (parsed) succeeded")
            return merged

    # --- 3) Partial merge failed or produced no effect: attempt more aggressive partial merge using regex fallback ---
    try:
        # Extract function/class blocks from candidate via regex and attempt replacements
        # This is a last-ditch attempt to salvage candidate fragments
        blocks = re.findall(r"(?:^|\n)((?:async\s+def|def|class)\s+[A-Za-z_]\w*[^\n]*:\n(?:\s+.*\n)+)", candidate, flags=re.MULTILINE)
        if blocks:
            tmp = merged
            replaced_any = False
            for blk in blocks:
                # get function/class name
                m = re.match(r"(?:async\s+def|def|class)\s+([A-Za-z_]\w*)", blk)
                if not m:
                    continue
                name = m.group(1)
                pattern = rf"(?:^|\n)(?:async\s+def|def|class)\s+{re.escape(name)}\b[^\n]*:\n(?:\s+.*\n)+"
                if re.search(pattern, tmp, flags=re.MULTILINE):
                    merged_candidate = _safe_replace_first(tmp, pattern, "\n" + blk + "\n")
                    if _parse_ok(merged_candidate):
                        tmp = merged_candidate
                        replaced_any = True
                        logger.info(f"merge_llm_result: regex replaced '{name}' block")
            if replaced_any and _parse_ok(tmp):
                return tmp
    except Exception as e:
        logger.debug("merge_llm_result: regex partial merge step failed: %s", e)

    # --- 4) No partial changes possible. If allow_full_rewrite -> attempt function-level rewrite fallback ---
    if allow_full_rewrite:
        # Extract candidate function/class blocks and try replacing them wholesale (even if candidate didn't parse)
        blocks = re.findall(r"(?:^|\n)((?:async\s+def|def|class)\s+[A-Za-z_]\w*[^\n]*:\n(?:\s+.*\n)+)", llm_out, flags=re.MULTILINE)
        if blocks:
            tmp = base
            changed = False
            for blk in blocks:
                m = re.match(r"(?:async\s+def|def|class)\s+([A-Za-z_]\w*)", blk)
                if not m:
                    continue
                name = m.group(1)
                # replace function body in base if present
                pattern = rf"(?:^|\n)(?:async\s+def|def|class)\s+{re.escape(name)}\b[^\n]*:\n(?:\s+.*\n)+"
                if re.search(pattern, tmp, flags=re.MULTILINE):
                    candidate_replacement = _safe_replace_first(tmp, pattern, "\n" + blk + "\n")
                    if _parse_ok(candidate_replacement):
                        tmp = candidate_replacement
                        changed = True
                        logger.info(f"merge_llm_result: full-function rewrite replaced '{name}' successfully")
            if changed and _parse_ok(tmp):
                # Final hallucination checks
                base_names = set(_top_level_names(base))
                tmp_names = set(_top_level_names(tmp))
                added = tmp_names - base_names
                base_imports = set(_imports_from_code(base))
                tmp_imports = set(_imports_from_code(tmp))
                new_imports = tmp_imports - base_imports
                if len(added) > MAX_ADDED_TOPLEVEL_DEFS or len(new_imports) > MAX_ADDED_IMPORTS:
                    logger.warning("merge_llm_result: rejecting full-function rewrite due to excessive additions")
                    return base
                logger.info("merge_llm_result: accepted full-function rewrite (allow_full_rewrite=True)")
                return tmp

    # --- 5) fallback: no safe merge - return base unchanged ---
    logger.debug("merge_llm_result: falling back to base (no safe merge applied)")
    return base
