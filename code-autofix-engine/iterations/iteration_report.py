# iterations/iteration_report.py
import json
from datetime import datetime

def create_iteration_report(iteration, code, stdout, stderr, fix_method, error_type=None, success=False, exec_time=None):
    """
    Creates a structured JSON-friendly report for each iteration.

    Parameters:
    - iteration (int): iteration number
    - code (str): code snapshot after fix
    - stdout (str): standard output from sandbox
    - stderr (str): error output from sandbox
    - fix_method (str): AST or LLM
    - error_type (str, optional): detected error type
    - success (bool, optional): whether code ran successfully this iteration
    - exec_time (float, optional): execution duration in seconds
    """
    return {
        "iteration": iteration,
        "timestamp": datetime.now().isoformat(),
        "fix_method": fix_method,
        "error_type": error_type,
        "success": success,
        "execution_time": exec_time,
        "stdout": stdout,
        "stderr": stderr,
        "code_snapshot": code
    }


def save_full_report(iteration_reports, change_log, final_status,base_file_path="iterations/report"):
    """
    Saves full debugging report as JSON with timestamped filename.

    Returns: path to saved JSON report
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = f"{base_file_path}_{timestamp}.json"

    data = {
        "final_status": final_status,
        "total_iterations": len(iteration_reports),
        "iterations": iteration_reports,
        "changes": change_log
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"[REPORT] Saved iteration report to: {file_path}")
    return file_path


def print_report_summary(iteration_reports, final_status):
    """Optional helper to print a readable summary to console."""
    print(f"\n=== Debugging Report Summary ===")
    print(f"Final Status: {final_status}")
    print(f"Total Iterations: {len(iteration_reports)}")
    for it in iteration_reports:
        print(f"\n--- Iteration {it['iteration']} ---")
        print(f"Fix Method: {it['fix_method']}")
        print(f"Error Type: {it.get('error_type')}")
        print(f"Success: {it.get('success')}")
        if it.get('execution_time') is not None:
            print(f"Execution Time: {it['execution_time']:.2f}s")
        print(f"Stdout: {it['stdout']}")
        print(f"Stderr: {it['stderr']}")
