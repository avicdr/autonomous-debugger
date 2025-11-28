# config/settings.py
"""
Centralized settings for the local auto-fix engine.
Adjust these values for your environment.
"""

# Repair loop
MAX_ITERATIONS = 5

# Sandbox
SANDBOX_TIMEOUT = 6  # seconds; used by sandbox_runner to wait for sandbox/main.py
# Note: sandbox/main.py itself uses SANDBOX_TIME_LIMIT env var for child limits.

# Model / LLM
MODEL_BACKEND = "llama_cpp" # options: "ollama", "llama_cpp"
MODEL_NAME = "qwen2.5-coder-7b-instruct-q4_k_m"   # Ollama-style name or local GGUF basename
MODEL_MAX_TOKENS = 400

# Logging / debug
DEBUG = True
