from pydantic import BaseModel
from typing import Literal, List, Dict


class IncidentAction(BaseModel):
    """Action taken by the agent during an incident triage step."""
    root_cause: str
    severity: Literal["P1", "P2", "P3"]
    remediation: Literal[
        "rollback_deployment",
        "scale_out",
        "restart_service",
        "escalate_to_engineer",
        "snooze_alert",
        "flush_cache",
        "failover_db",
    ]
    summary: str  # One-line, max 120 chars


class IncidentObservation(BaseModel):
    """What the agent observes at each step."""
    step: int
    task_name: str = ""
    scenario_id: str = ""
    alerts: List[Dict]
    log_snippets: List[str]
    dependency_graph: Dict
    recent_deployments: List[Dict]
    task_description: str
    reward: float
    done: bool
    feedback: str


class IncidentState(BaseModel):
    """Internal episode state."""
    episode_id: str = ""
    step_count: int = 0
    task_name: str = ""
    scenario_id: str = ""
    total_reward: float = 0.0
    solved: bool = False
