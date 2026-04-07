#!/usr/bin/env python3
"""
Baseline inference script for incident_triage_env.
Emits [START], [STEP], [END] lines to stdout per the OpenEnv spec.
"""
import os
import sys
import json
import time

from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN     = os.getenv("HF_TOKEN")
ENV_URL      = os.getenv("ENV_URL", "http://localhost:8000")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

TASKS    = ["easy", "medium", "hard"]
ENV_NAME = "incident_triage_env"

SYSTEM_PROMPT = """You are an expert SRE (Site Reliability Engineer) agent.
You receive incident data: alerts, log snippets, service dependency graph, and recent deployments.
Your job:
1. Identify root_cause — the service/component at fault (e.g. "postgres-primary", "redis-cache")
2. Assess severity — P1 (total outage/revenue impact), P2 (major degradation), P3 (minor)
3. Choose remediation — one of: rollback_deployment, scale_out, restart_service, escalate_to_engineer, snooze_alert, flush_cache, failover_db
4. Write summary — one line, max 120 chars

Respond ONLY with valid JSON, no preamble, no markdown:
{"root_cause": "...", "severity": "P1|P2|P3", "remediation": "...", "summary": "..."}"""


def format_obs(obs: dict) -> str:
    return (
        f"TASK: {obs.get('task_description', '')}\n\n"
        f"ALERTS:\n{json.dumps(obs.get('alerts', []), indent=2)}\n\n"
        f"LOG SNIPPETS:\n" + "\n".join(obs.get("log_snippets", [])) + "\n\n"
        f"DEPENDENCY GRAPH:\n{json.dumps(obs.get('dependency_graph', {}), indent=2)}\n\n"
        f"RECENT DEPLOYMENTS:\n{json.dumps(obs.get('recent_deployments', []), indent=2)}"
    )


def get_action(obs: dict) -> dict:
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": format_obs(obs)},
        ],
        max_tokens=300,
        temperature=0.0,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def call_env(method: str, payload: dict = None) -> dict:
    import urllib.request
    data = json.dumps(payload or {}).encode()
    req  = urllib.request.Request(
        f"{ENV_URL}/{method}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def run_task(task_name: str):
    rewards   = []
    step_n    = 0
    done      = False
    error_msg = "null"

    print(f"[START] task={task_name} env={ENV_NAME} model={MODEL_NAME}", flush=True)

    try:
        result = call_env("reset", {"task": task_name})
        obs    = result.get("observation", result)

        while not done:
            step_n += 1
            try:
                action_dict = get_action(obs)
                action_str  = json.dumps(action_dict, separators=(",", ":"))
                result      = call_env("step", action_dict)
                obs         = result.get("observation", result)
                reward      = float(obs.get("reward", 0.0))
                done        = bool(obs.get("done", False))
                error_msg   = "null"
            except Exception as e:
                reward    = 0.0
                done      = True
                error_msg = str(e).replace("\n", " ")[:200]
                action_str = "error"

            rewards.append(reward)
            print(
                f"[STEP] step={step_n} action={action_str} "
                f"reward={reward:.2f} done={str(done).lower()} error={error_msg}",
                flush=True,
            )

    except Exception as e:
        error_msg = str(e).replace("\n", " ")[:200]
        rewards   = [0.0]
        step_n    = max(step_n, 1)
        print(
            f"[STEP] step={step_n} action=null reward=0.00 done=true error={error_msg}",
            flush=True,
        )

    rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.00"
    success     = any(r >= 0.5 for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={step_n} rewards={rewards_str}",
        flush=True,
    )


if __name__ == "__main__":
    for task in TASKS:
        try:
            run_task(task)
        except Exception as e:
            print(f"[END] success=false steps=0 rewards=0.00", flush=True)
            print(f"FATAL: {e}", file=sys.stderr)
        time.sleep(1)
