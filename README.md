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

Production incidents cost companies millions per hour of downtime. SRE engineers must rapidly
correlate alerts, logs, and deployment history to identify root cause and act — often in under
5 minutes. This environment simulates that workflow for training and evaluating AI agents on
real-world infrastructure reasoning tasks.

An agent receives a snapshot of a live production incident: firing alerts with thresholds, recent
error log snippets, a service dependency graph, and recent deployment history. It must output a
structured triage decision.

This environment fills a real gap — no existing OpenEnv benchmark tests agentic root cause analysis
with multi-signal correlated observations in SRE workflows. On-call incident response is a daily
workflow at every tech company running microservices.

## Action Space

| Field | Type | Values |
|---|---|---|
| root_cause | str | Service name (e.g. "postgres-primary", "redis-cache", "feature-flag-service") |
| severity | enum | P1 (full outage/revenue impact), P2 (major degradation), P3 (minor issue) |
| remediation | enum | rollback_deployment, scale_out, restart_service, escalate_to_engineer, snooze_alert, flush_cache, failover_db |
| summary | str | One-line incident description, 10–120 chars |

## Observation Space

| Field | Type | Description |
|---|---|---|
| step | int | Current step number within the episode |
| task_name | str | Active task name (easy / medium / hard) |
| scenario_id | str | ID of the current scenario being triaged |
| alerts | List[Dict] | Firing alerts: service, metric, value, threshold, firing_for |
| log_snippets | List[str] | Recent error/warn log lines from affected services |
| dependency_graph | Dict | Service → list of downstream services it depends on |
| recent_deployments | List[Dict] | Deployments in the last 2 hours with version notes |
| task_description | str | Natural language objective for this episode |
| reward | float | Reward earned by the last action (0.0 on first observation) |
| done | bool | Whether all scenarios in this episode are complete |
| feedback | str | Breakdown of last action's score by component |

## Reward Function

Reward is shaped across four components per incident — not binary end-of-episode:

| Component | Max | Partial Credit |
|---|---|---|
| Root cause identification | 0.4 | 0.2 for substring/family match |
| Severity classification | 0.2 | 0.1 for adjacent severity (P1↔P2 or P2↔P3) |
| Remediation action | 0.3 | None — exact match required |
| Incident summary quality | 0.1 | 0.05 if present but generic |

Graders are fully deterministic — same action always returns same score.

## Tasks

| Task | Difficulty | Scenarios | Description |
|---|---|---|---|
| easy | Easy | 3 | Single-service failures. Clear log trail, no cascading. |
| medium | Medium | 3 | Cascading failures across 2–3 services. Deployment red herrings present. |
| hard | Hard | 3 | Full outages, silent data pipeline failures, tenant-specific 503s with minimal signal. |

### Hard task design note

Hard scenarios are designed to challenge frontier models:
- `hard_1`: Feature-flag service disables its own cache and causes a cascading DB lock across 4 services
- `hard_2`: Silent ETL deadlock — no error alerts, only duration metrics firing
- `hard_3`: Tenant-specific 0.1% failure rate for VIP enterprise accounts via license server rate limiting

## Setup & Usage

### Docker (local)

```bash
docker build -t incident-triage-env:latest -f server/Dockerfile .
docker run -d -p 8000:8000 incident-triage-env:latest
curl http://localhost:8000/health
```

### Run baseline inference

```bash
HF_TOKEN=your_token \
API_BASE_URL=https://router.huggingface.co/v1 \
MODEL_NAME=meta-llama/Llama-3.3-70B-Instruct \
ENV_URL=http://localhost:8000 \
python inference.py
```

### Validate OpenEnv spec

```bash
openenv validate --verbose
```

## Baseline Performance

Measured over 2 complete runs with `meta-llama/Llama-3.3-70B-Instruct` at temperature 0
via `https://router.huggingface.co/v1`. Results are deterministic (temperature=0).

| Task | Avg Reward | Notes |
|---|---|---|
| easy | 0.95 | Perfect on root cause and remediation; easy_2 loses 0.15 on severity off-by-one and generic summary |
| medium | 0.82 | medium_2 misidentifies postgres-primary vs postgres-replica (wrong root cause, partial credit only) |
| hard | 1.00 | Correctly traces cascading DB lock, silent ETL deadlock, and tenant-specific license failure |
