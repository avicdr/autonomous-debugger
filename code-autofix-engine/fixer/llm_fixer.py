# fixer/llm_fixer.py
"""
LLM-based fixer wrapper.

Now accepts `logic_issues` (list) to include in prompt to guide LLM.
Returns cleaned Python code (or empty string on failure).
"""
from __future__ import annotations

import ast
import logging
import re
from typing import Optional, List

from models.qwen_runner import qwen_generate

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """You are a local code assistant. The user provided the following code:

###
{code}
###

It produced this error:

###
{error}
###

Detected logical issues (if any):
###
{logic}
###

User instructions:
{user_instructions}

Please return only the corrected Python file contents (no explanation, no markdown, no fences).
If you cannot safely fix the program, return an empty string.
"""

MAX_OUTPUT_CHARS = 20000

def _is_valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except Exception:
        return False

def _extract_code_from_text(text: str) -> str:
    if not text:
        return ""
    fence_match = re.search(r"```(?:python)?\n(.*?)```", text, re.S | re.I)
    if fence_match:
        candidate = fence_match.group(1).strip()
        if _is_valid_python(candidate):
            return candidate + "\n"
        candidate2 = re.sub(r"^\s*#.*\n+", "", candidate)
        if _is_valid_python(candidate2):
            return candidate2 + "\n"

    lines = text.splitlines()
    best = ""
    for i in range(len(lines)):
        for j in range(i + 1, min(len(lines), i + 200) + 1):
            block = "\n".join(lines[i:j]).strip()
            if len(block) < 10:
                continue
            if _is_valid_python(block) and len(block) > len(best):
                best = block
    if best:
        return best + "\n"

    cleaned = re.sub(r"^[A-Za-z ,\-\(\)\"']+:\s*", "", text).strip()
    if _is_valid_python(cleaned):
        return cleaned + "\n"

    return text.strip()[:MAX_OUTPUT_CHARS]

def clean_llm_code(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"^```(?:python)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()
    extracted = _extract_code_from_text(text)
    return extracted if extracted.endswith("\n") else extracted + ("\n" if extracted else "")

def generate_llm_fix(
    code: str,
    error_message: str,
    user_prompt: str,
    logic_issues: Optional[List[dict]] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Ask the local LLM to produce a corrected file. Returns the cleaned code (possibly empty).
    """
    logic_text = ""
    if logic_issues:
        # summarize top issues (limit to a few)
        parts = []
        for idx, it in enumerate(logic_issues[:6]):
            t = f"- {it.get('issue_type')}: {it.get('message')}"
            parts.append(t)
        logic_text = "\n".join(parts)
    prompt = _PROMPT_TEMPLATE.format(code=code, error=error_message or "<none>", user_instructions=user_prompt or "", logic=logic_text)

    try:
        raw = qwen_generate(prompt, max_tokens=max_tokens)
        if not raw:
            logger.warning("LLM returned empty response.")
            return ""
        cleaned = clean_llm_code(raw)
        if cleaned and _is_valid_python(cleaned):
            return cleaned
        candidate = _extract_code_from_text(raw)
        if candidate and _is_valid_python(candidate):
            return candidate
        if _is_valid_python(raw):
            return raw
        logger.warning("LLM output could not be parsed as Python after cleaning.")
        return ""
    except Exception as e:
        logger.error(f"LLM fix generation failed: {e}")
        return ""
