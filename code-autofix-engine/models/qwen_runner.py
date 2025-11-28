# qwen_runner.py
"""
Optimized ultra-fast runner for Qwen2.5-Coder-7B-Instruct-Q4_K_M

Key improvements:
- Fast greedy decoding
- KV cache
- GPU offload
- Reduced prompt size
- Faster regex cleaning
- Lightweight code extraction
- Lower overhead for llama.cpp calls
"""

from __future__ import annotations
import logging
import subprocess
import re
from config.settings import MODEL_BACKEND, MODEL_NAME, MODEL_MAX_TOKENS

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

logger = logging.getLogger(__name__)
llama_model = None


# ============================================================
# FAST INITIALIZER (llama.cpp)
# ============================================================
def init_llama():
    global llama_model
    if llama_model is not None:
        return

    if not Llama:
        raise ImportError("llama_cpp is not installed")

    # ⚡ Optimized llama.cpp settings
    llama_model = Llama(
        model_path=f"models/gguf/{MODEL_NAME}.gguf",
        n_ctx=4096,                 # 4096 is enough for debugging
        n_threads=4,                # Avoid overhead from too many threads
        n_gpu_layers=999,           # Full GPU offload if available
        use_mlock=False,
        use_mmap=True,
        embedding=False,
        logits_all=False,           # Faster
        verbose=False,              # Reduce logging overhead
    )

    logger.info("⚡ Fast Llama.cpp Qwen model loaded.")


# ============================================================
# QWEN CHAT TEMPLATE (FAST)
# ============================================================
def build_qwen_chat(prompt_text: str):
    """
    Keep it minimal — large prompts slow down generation.
    """
    return (
        "<|im_start|>system\n"
        "You are Qwen, a helpful Python code-fixing assistant.<|im_end|>\n"
        "<|im_start|>user\n" +
        prompt_text +
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


# ============================================================
# VERY FAST OUTPUT CLEANER
# ============================================================
_fast_strip_tokens = re.compile(r"<\|im.*?\|>", re.S)

def clean_llm_output(text: str):
    if not text:
        return ""

    # Remove special tokens
    text = _fast_strip_tokens.sub("", text)

    # Remove markdown backticks
    if "```" in text:
        text = text.replace("```python", "").replace("```", "")

    return text.strip()


# ============================================================
# FAST PURE CODE EXTRACTION
# ============================================================
def extract_pure_code(text: str):
    if not text:
        return ""

    # If response smells like instructions → reject (saves iterations)
    lt = text.lower()
    if lt.startswith("you are ") or "user provided" in lt:
        return ""

    # Return text as-is — LLM is already instructed to output ONLY code
    return text.strip()


# ============================================================
# FAST llama.cpp GENERATION
# ============================================================
def run_llama_cpp(prompt: str, max_tokens=None):
    if llama_model is None:
        init_llama()

    max_tokens = max_tokens or MODEL_MAX_TOKENS or 256

    try:
        full_prompt = build_qwen_chat(prompt)

        # ⚡ Greedy decoding = fastest
        out = llama_model(
            full_prompt,
            max_tokens=max_tokens,
            temperature=0.0,
            top_p=0.9,
            stop=["<|im_end|>"],
            repeat_penalty=1.0,     # Lower penalty → faster & more stable for code
        )

        raw = out["choices"][0]["text"]

        cleaned = clean_llm_output(raw)
        code = extract_pure_code(cleaned)

        return code

    except Exception as e:
        logger.error(f"Llama.cpp generation failed: {e}")
        return ""


# ============================================================
# OLLAMA BACKEND (FAST WRAPPER)
# ============================================================
def run_ollama(prompt: str, timeout=25):
    try:
        proc = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, err = proc.communicate(input=prompt, timeout=timeout)

        if err:
            logger.warning(f"Ollama stderr: {err}")

        return clean_llm_output(out)

    except Exception as e:
        logger.error(f"Ollama failed: {e}")
        return ""


# ============================================================
# UNIFIED ENTRY POINT
# ============================================================
def qwen_generate(prompt: str, max_tokens: int = None) -> str:
    """
    Fast unified generator.
    """
    if MODEL_BACKEND == "llama_cpp":
        return run_llama_cpp(prompt, max_tokens)

    elif MODEL_BACKEND == "ollama":
        return run_ollama(prompt)

    raise ValueError(f"Unknown backend: {MODEL_BACKEND}")
