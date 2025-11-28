# main.py
"""
Entry point for the Local Code Auto-Fix Engine.

Modes:
1. Interactive  -> Asks user for code + prompt
2. Test mode    -> Auto-loads a random buggy code snippet + random prompt
                   Run using:
                       python main.py --test
"""

import sys
import random
from iterations.iteration_controller import run_repair_loop
from utils.logger import log_header, log_step
from config.settings import MAX_ITERATIONS


TEST_CODES = [

    # -------------------------------------------------------
    # 1. Logical factorial bug (wrong base-case)
    # -------------------------------------------------------
    """def fib(n, memo={}):
    if n <= 1:
        return n

    if n in memo:
        return memo[0]   # BUG: wrong key returned

    memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]

print(fib(10))


""",
]

TEST_PROMPTS = [
    "Fix all errors and make the program run correctly.",
    "Correct syntax issues and produce valid output.",
    "Repair the code so it executes without errors.",
    "Make this function work as intended.",
    "Fix bugs and return the correct result.",
]


# -----------------------
# Main Logic
# -----------------------
def run_interactive():
    """Interactive user input mode."""
    print("\n=== Local Code Auto-Fix Engine ===\n")

    user_code = input("Paste your Python code:\n\n")
    if not user_code.strip():
        print("No code provided. Exiting.")
        return

    user_prompt = input("\nDescribe what the code should do:\n\n")
    if not user_prompt.strip():
        print("No instructions provided. Proceeding with default repair.")

    execute_repair(user_code, user_prompt)


def run_test_mode():
    """Automatically run a random test case."""
    print("\n=== Running RANDOM TEST MODE ===\n")

    user_code = random.choice(TEST_CODES)
    user_prompt = random.choice(TEST_PROMPTS)

    print("===== RANDOM TEST CODE =====")
    print(user_code)
    print("============================\n")

    print("===== RANDOM PROMPT =====")
    print(user_prompt)
    print("=========================\n")

    execute_repair(user_code, user_prompt)


def execute_repair(code, prompt):
    """Runs repair loop and prints final output and report path."""
    log_header("=== Starting Repair Loop ===")

    final_code, report_path = run_repair_loop(
        original_code=code,
        user_prompt=prompt,
        max_iterations=MAX_ITERATIONS
    )

    log_header("=== Repair Completed ===")
    print("\n======================= FINAL FIXED CODE =======================")
    print(final_code)
    print("===============================================================\n")

    print(f"Debugging report saved at: {report_path}")


# -----------------------
# Entry Point
# -----------------------
if __name__ == "__main__":
    if "--test" in sys.argv:
        run_test_mode()
    else:
        run_interactive()
