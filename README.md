---
title: Incident Triage Environment
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
app_port: 8000
tags:
  - openenv
  - real-world
  - sre
  - incident-management
---

# Incident Triage Environment

## Overview & Motivation

Production incidents cost companies millions per hour of downtime. 
SRE engineers must rapidly correlate alerts, logs, and deployment 
history to identify root cause and act — often in under 5 minutes. 
This environment simulates that workflow for training and evaluating 
AI agents on real-world infrastructure reasoning tasks.

An agent receives a snapshot of a live production incident: firing 
alerts with thresholds, recent error log snippets, a service 
dependency graph, and recent deployment history. It must output a 
structured triage decision in one shot.

No existing RL benchmark tests agentic root cause analysis with 
multi-signal correlated observations in SRE workflows. This 
environment fills that gap directly — with immediate value for 
teams building and evaluating ops agents.

## Action Space

| Field | Type | Values |
|---|---|---|
| root_cause | str | Service name (e.g. "postgres-primary", "redis-cache") |
| severity | enum | P1 (full outage/revenue impact), P2 (major degradation), P3 (minor) |
| remediation | enum | rollback_deployment, scale_out, restart_service, escalate_to_engineer, snooze_alert, flush_cache, failover_db |
| summary | str | One-line incident description, 10–120 chars |

## Observation Space

| Field | Type | Description |
|---|---|---|
| step | int | Current step within the episode |
| alerts | List[Dict] | Firing alerts: service, metric, value, threshold, firing_for |
| log_snippets | List[str] | Recent error/warn logs from affected services |
| dependency_graph | Dict | Service → list of downstream dependencies |
| recent_deployments | List[Dict] | Deployments in last 2 hours with version and notes |
| task_description | str | Natural language goal for this episode |
| reward | float | Reward from last action, strictly in (0, 1) |
| done | bool | Whether all scenarios in this episode are complete |
| feedback | str | Per-component score breakdown of last action |

## Reward Function

Reward is shaped across four components per incident — not binary 
end-of-episode. All rewards are strictly within (0, 1).

| Component | Max | Partial Credit |
|---|---|---|
| Root cause identification | 0.4 | 0.2 for substring/family match |
| Severity classification | 0.2 | 0.1 for adjacent severity (P1↔P2) |
| Remediation action | 0.3 | None — exact match required |
| Incident summary quality | 0.1 | 0.05 if present but generic |

Graders are fully deterministic — same action always returns same score.

## Tasks

| Task | Difficulty | Scenarios | Avg Agent Score |
|---|---|---|---|
| easy | Easy | 3 | ~0.98 |
| medium | Medium | 3 | ~0.47 |
| hard | Hard | 3 | ~0.35 |

### Task Design

**Easy** — Single-service failures with clear log trails. 
No cascading. Agent can identify root cause from direct evidence.

**Medium** — Cascading failures across 2–3 services. Misleading 
recent deployments present as red herrings. Agent must trace 
dependency chain to find origin.

**Hard** — Full outages with indirect signals only. Logs show 
downstream symptoms, never root cause directly. Multiple red 
herring deployments. Agent must reason across 5+ services to 
identify the origin.

### Hard Task Design Note

Hard scenarios are specifically designed to challenge frontier 
models. Logs never name the root cause service directly — only 
downstream symptoms are visible. The LLM must correlate alert 
timing, deployment history, and dependency graph structure to 
reach the correct conclusion. Llama-3.3-70B scores ~0.35 average 
on hard tasks.

## Setup & Usage

### Docker

```bash
docker build -t incident-triage-env:latest -f server/Dockerfile .
docker run -d -p 8000:8000 incident-triage-env:latest
curl http://localhost:8000/health
```

### Run baseline inference

```bash
HF_TOKEN=your_token \
ENV_URL=http://localhost:8000 \
python inference.py
```

### Validate OpenEnv spec

```bash
openenv validate --verbose
```

### Connect via client

```python
from incident_triage_env import IncidentAction, IncidentTriageEnv

with IncidentTriageEnv(base_url="https://samyuktha-12-incident-triage-env.hf.space") as env:
    obs = env.reset(task="hard")
    result = env.step(IncidentAction(
        root_cause="feature-flag-service",
        severity="P1",
        remediation="rollback_deployment",
        summary="feature-flag-service cache disabled causing cascading DB lock"
    ))
    print(result.observation.reward)
    print(result.observation.feedback)
```

## Baseline Performance

Tested with Llama-3.3-70B-Instruct at temperature 0:

| Task | Rewards | Avg | Notes |
|---|---|---|---|
| easy | 0.99, 0.95, 0.99 | 0.98 | Strong — direct evidence available |
| medium | 0.70, 0.25, 0.45 | 0.47 | Cascading failures and red herrings confuse model |
| hard | 0.25, 0.55, 0.25 | 0.35 | Indirect signals only — frontier model struggles |

## Why This Environment Matters

SRE incident response is a high-stakes, time-pressured workflow 
that every technology company depends on. Training agents to 
reason over correlated multi-signal observations — alerts, logs, 
dependency graphs, deployment history simultaneously — is an 
unsolved problem in the RL/agent space.

This environment provides the first structured benchmark for 
evaluating agent performance on production incident triage, 
with clear difficulty progression and deterministic grading.
