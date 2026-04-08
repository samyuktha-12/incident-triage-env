#!/usr/bin/env python3
"""
Demo script for the Incident Triage Environment.
Submits perfect ground-truth actions directly — no LLM or API key required.

Usage:
  python demo.py                                      # uses localhost:8000
  ENV_URL=https://your-space.hf.space python demo.py
"""
import os
import json
import urllib.request

ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")

# Perfect ground-truth actions per scenario
PERFECT_ACTIONS = {
    "easy": [
        {
            "root_cause": "postgres-primary",
            "severity": "P1",
            "remediation": "scale_out",
            "summary": "postgres-primary connection pool exhausted",
        },
        {
            "root_cause": "recommendation-service",
            "severity": "P1",
            "remediation": "rollback_deployment",
            "summary": "recommendation-service crash loop after bad deployment",
        },
        {
            "root_cause": "search-service",
            "severity": "P2",
            "remediation": "restart_service",
            "summary": "search-service out of memory heap exhausted",
        },
    ],
    "medium": [
        {
            "root_cause": "redis-cache",
            "severity": "P1",
            "remediation": "restart_service",
            "summary": "redis-cache OOM causing cascading auth failures",
        },
        {
            "root_cause": "postgres-replica",
            "severity": "P1",
            "remediation": "failover_db",
            "summary": "postgres-replica lag causing payment consistency errors",
        },
        {
            "root_cause": "api-gateway",
            "severity": "P2",
            "remediation": "rollback_deployment",
            "summary": "api-gateway deployment killing CDN cache hit rate",
        },
    ],
    "hard": [
        {
            "root_cause": "feature-flag-service",
            "severity": "P1",
            "remediation": "rollback_deployment",
            "summary": "feature-flag-service cache disabled causing cascade",
        },
        {
            "root_cause": "etl-pipeline",
            "severity": "P2",
            "remediation": "restart_service",
            "summary": "etl-pipeline deadlock on warehouse table lock",
        },
        {
            "root_cause": "license-server",
            "severity": "P1",
            "remediation": "escalate_to_engineer",
            "summary": "license-server rate limited causing enterprise 503s",
        },
    ],
    "chaos": [
        {
            "root_cause": "postgres-primary",
            "severity": "P1",
            "remediation": "scale_out",
            "summary": "postgres-primary connection pool causing payment slowdown amid recommendation crash",
        },
        {
            "root_cause": "redis-cache",
            "severity": "P1",
            "remediation": "restart_service",
            "summary": "redis-cache OOM causing auth failures and notification backlog",
        },
        {
            "root_cause": "postgres-replica",
            "severity": "P1",
            "remediation": "failover_db",
            "summary": "postgres-replica lag causing duplicate payment transactions",
        },
    ],
}

DIVIDER = "━" * 40


def call_env(method: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{ENV_URL}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def run_task(task_name: str) -> list[float]:
    result = call_env("reset", {"task": task_name})
    obs = result.get("observation", result)

    rewards = []
    actions = PERFECT_ACTIONS[task_name]

    for i, action in enumerate(actions):
        scenario_id = obs.get("task_description", "")

        result = call_env("step", action)
        obs = result.get("observation", result)

        reward = float(obs.get("reward", 0.0))
        feedback = obs.get("feedback", "")
        done = bool(obs.get("done", False))
        rewards.append(reward)

        # Derive scenario ID from task + index
        scenario_label = f"{task_name}_{i + 1}"

        print(DIVIDER)
        print(f"TASK: {task_name} | SCENARIO: {scenario_label}")
        print(f"ACTION: {action['root_cause']} | {action['severity']} | {action['remediation']}")
        print(f"REWARD: {reward:.2f}")
        print(f"FEEDBACK: {feedback}")

        if done:
            break

    return rewards


def print_summary_table(results: dict[str, list[float]]):
    print()
    print("Final summary:")
    print("┌─────────┬────────┬───────┐")
    print("│ Task    │ Avg    │ Pass  │")
    print("├─────────┼────────┼───────┤")
    for task, rewards in results.items():
        avg = sum(rewards) / len(rewards) if rewards else 0.0
        passed = avg >= 0.5
        check = "✅" if passed else "❌"
        print(f"│ {task:<7} │ {avg:.2f}   │  {check}   │")
    print("└─────────┴────────┴───────┘")


def main():
    print(f"Connecting to environment at {ENV_URL}\n")

    results = {}
    for task in ["easy", "medium", "hard", "chaos"]:
        print(f"\n{'=' * 40}")
        print(f"Running task: {task.upper()}")
        print(f"{'=' * 40}")
        try:
            rewards = run_task(task)
            results[task] = rewards
        except Exception as e:
            print(f"ERROR running task '{task}': {e}")
            results[task] = [0.0]

    print(DIVIDER)
    print_summary_table(results)


if __name__ == "__main__":
    main()
