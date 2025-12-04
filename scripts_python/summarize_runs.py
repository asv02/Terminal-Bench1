#!/usr/bin/env python3
from collections import defaultdict
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import os
import glob

RUNS_ROOT = Path("runs").resolve()

TIMEOUT_KEYS = {"timeout", "agent_timeout", "test_timeout", "timed_out", "deadline_exceeded"}

def parse_batch_name(batch_dir: Path):
    """Example: github-action-claude-code-4-5-sonnet_hello-world-test_1"""
    agent_run = batch_dir.name.replace("github-action-", "")
    agent, task, run = agent_run.split("_")
    return agent, task, run

def safe_read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON file {p}: {e}")
        return None


def pass_at_k_estimator(n: int, c: int, k: int) -> float:
    """Calculates 1 - comb(n - c, k) / comb(n, k)."""
    if n - c < k:
        return 1.0
    return float(1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1)))


def get_difficulty(agents_summary: Dict[str, Dict[str, Any]]) -> str:
    # Ignore NOP and Oracle for difficulty calculation
    accuracies = [agent_summary["accuracy"] for agent, agent_summary in agents_summary.items() if agent not in ["nop", "oracle"]]
    if len(accuracies) == 0:
        return "n/a"
    elif any(accuracy < 0.4 for accuracy in accuracies):
        return "hard"
    elif any(accuracy < 0.6 for accuracy in accuracies):
        return "medium"
    elif any(accuracy < 0.8 for accuracy in accuracies):
        return "easy"
    else:
        return "trivial"


def main():
    if not RUNS_ROOT.exists():
        print(f"No runs directory found at {RUNS_ROOT}")
        return

    result_json_files = glob.glob(f"{RUNS_ROOT}/github-action-*/results.json")

    all_results: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for result_json_file in result_json_files:
        path = Path(result_json_file)
        results_json = safe_read_json(path)
        agent, task, _ = parse_batch_name(path.parent)
        print(f"Reading results from {result_json_file} for task {task} with agent {agent}")
        all_results[task][agent].extend(results_json.get("results", []))
    
    summary: Dict[str, Dict[str, Any]] = defaultdict(dict)
    for task, results_by_agent in all_results.items():
        agents_summary: Dict[str, Dict[str, Any]] = defaultdict(dict)
        summary[task]["tests_results"] = defaultdict(list)
        for agent, task_results in results_by_agent.items():
            print(f"Task results for task {task} with agent {agent}: {task_results}")
            is_resolveds = []
            n_agent_timeouts = 0
            n_other_failures = 0
            for result in task_results:
                # Treat None as False (unresolved)
                is_resolved = result["is_resolved"]
                is_resolveds.append(is_resolved if is_resolved is not None else False)
                if not is_resolved:
                    if result["failure_mode"] == "agent_timeout":
                        n_agent_timeouts += 1
                    else:
                        n_other_failures += 1
                # Get the parser_results
                if agent != "nop" and agent != "oracle":
                    # The parser_results is not always present, e.g., test_timeout
                    if "parser_results" in result and result["parser_results"] is not None:
                        for test_name, test_result in result["parser_results"].items():
                            summary[task]["tests_results"][test_name.split(" - ")[0]].append(test_result)
            agents_summary[agent]["accuracy"] = sum(is_resolveds) / len(is_resolveds)
            agents_summary[agent]["n_runs"] = len(task_results)
            agents_summary[agent]["n_resolved"] = sum(is_resolveds)
            agents_summary[agent]["n_agent_timeouts"] = n_agent_timeouts
            agents_summary[agent]["n_other_failures"] = n_other_failures

        # Check if the task is solvable by the agents (every test must be passed at least once (by any agent run)))
        summary[task]["solvable"] = all(any(result == "passed" for result in results_by_test) for results_by_test in summary[task]["tests_results"].values())
        summary[task]["agents"] = agents_summary
        summary[task]["difficulty"] = get_difficulty(agents_summary)
    with open("summary-of-runs-comment.md", "w") as f:
        for task, task_summary in summary.items():
            f.write(f"## Summary of Runs for \"{task}\"\n")
            if set(task_summary["agents"]) == {"nop", "oracle"}:
                f.write("This task is not tested with any agents as the Oracle solution failed. Please fix the Oracle solution and re-run the tests.\n")
            else:
                f.write(f"### Difficulty: {task_summary['difficulty']}\n")
                f.write("| Agent/Model | # of total runs | # of successes | # of failures<br>(agent timeout) | # of failures<br>(other reasons) | Accuracy |\n")
                f.write("|-------------|-----------------|-----------------|------------------------------------|---------------|----------|\n")
                for agent, data in task_summary["agents"].items():
                    f.write(f"| {agent} | {data['n_runs']} | {data['n_resolved']} | {data['n_agent_timeouts']} | {data['n_other_failures']} | {data['accuracy']} |\n")

                # Print the tests result
                f.write("<details>\n")
                f.write("<summary>Tests Result</summary>\n\n")
                if task_summary["solvable"]:
                    f.write("✅ This task is solvable by the agents.\n")
                else:
                    f.write("⚠️ Some tests are not passed by any agent run. It's not clear if this task is solvable or simply super hard.\n")
                f.write("| Test Name | Successful Runs / Total Runs |\n")
                f.write("|-------------|------------------------------|\n")
                for test_name, test_result in task_summary["tests_results"].items():
                    f.write(f"| {test_name} | {sum(1 for result in test_result if result == "passed")} / {len(test_result)} |\n")
                f.write("</details>\n\n")
                debug = safe_read_json(Path(f"debug-output-{task}.json"))
                # Replace "pass" with "✅" and "fail" with "❌"
                debug["outcome"] = debug["outcome"].replace("PASS", "✅ PASS").replace("FAIL", "❌ FAIL").replace("NOT_APPLICABLE", "➖ NOT_APPLICABLE")
                f.write("### Analysis on Agent Failures\n")
                f.write("| Check       | Outcome  | Explanation              |\n")
                f.write("|-------------|----------|--------------------------|\n")
                f.write(f"| Task Instruction Sufficiency | {debug['outcome']} | {debug['explanation']} |\n")
        f.write("<!-- test-summary-end -->")
    # Send the difficulty of the last task to $GITHUB_OUTPUT
    # Note: last task but it should be fine as a PR should only contain one task
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"difficulty=difficulty:{summary[task]['difficulty']}\n")
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"solvable={summary[task]['solvable']}\n")

if __name__ == "__main__":
    main()