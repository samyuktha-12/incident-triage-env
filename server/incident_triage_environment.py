import uuid

try:
    from ..models import IncidentAction, IncidentObservation, IncidentState
    from .scenarios import ALL_SCENARIOS
except ImportError:
    try:
        from models import IncidentAction, IncidentObservation, IncidentState
        from scenarios import ALL_SCENARIOS
    except ImportError:
        from models import IncidentAction, IncidentObservation, IncidentState
        from server.scenarios import ALL_SCENARIOS

from openenv.core.env_server import Environment


class IncidentTriageEnvironment(Environment):
    """
    SRE Incident Triage Environment.

    Uses a singleton shared instance (see server/app.py) so that state is
    preserved across reset(), step(), and state property calls despite the
    openenv framework creating a new env reference per request.

    reset() and step() accept task/scenario_id as kwargs so they remain
    correct even when called on a fresh instance (stateless fallback).
    Reward is shaped across 4 components per incident.
    """

    def __init__(self, task_name: str = "easy"):
        super().__init__()
        self.task_name = task_name
        self._state = IncidentState()

    def close(self) -> None:
        """No-op: prevents the framework from destroying the shared singleton."""
        pass

    def reset(self, task: str = "easy", **kwargs) -> IncidentObservation:
        scenarios = ALL_SCENARIOS.get(task, ALL_SCENARIOS["easy"])
        scenario = scenarios[0]
        self._state = IncidentState(
            episode_id=str(uuid.uuid4()),
            task_name=task,
            scenario_id=scenario["id"],
            step_count=0,
            total_reward=0.0,
            solved=False,
        )
        return self._make_obs(
            scenario, task=task, step=0, reward=0.0, done=False,
            feedback="Incident detected. Begin triage.",
        )

    def step(self, action: IncidentAction, task: str = "easy", scenario_id: str = "", **kwargs) -> IncidentObservation:
        scenarios = ALL_SCENARIOS.get(task, ALL_SCENARIOS["easy"])
        idx = next((i for i, s in enumerate(scenarios) if s["id"] == scenario_id), 0)
        current = scenarios[idx]

        reward, feedback = self._grade(action, current)

        self._state.step_count += 1
        self._state.total_reward = round(self._state.total_reward + reward, 2)
        self._state.task_name = task

        next_idx = idx + 1
        done = next_idx >= len(scenarios)

        if not done:
            next_scenario = scenarios[next_idx]
            self._state.scenario_id = next_scenario["id"]
            return self._make_obs(
                next_scenario, task=task, step=idx + 1,
                reward=reward, done=False, feedback=feedback,
            )

        self._state.scenario_id = scenario_id
        self._state.solved = reward >= 0.7
        return IncidentObservation(
            step=idx + 1,
            task_name=task,
            scenario_id=scenario_id,
            alerts=[],
            log_snippets=[],
            dependency_graph={},
            recent_deployments=[],
            task_description="Episode complete.",
            reward=reward,
            done=True,
            feedback=feedback,
        )

    def _grade(self, action: IncidentAction, scenario: dict) -> tuple:
        gt = scenario["ground_truth"]
        score = 0.0
        parts = []

        # Root cause: 0.4 pts (exact), 0.2 pts (substring match)
        if action.root_cause == gt["root_cause"]:
            score += 0.4
            parts.append("root_cause correct (+0.4)")
        elif gt["root_cause"] in action.root_cause or action.root_cause in gt["root_cause"]:
            score += 0.2
            parts.append("root_cause partial (+0.2)")
        else:
            parts.append(f"root_cause wrong (expected: {gt['root_cause']})")

        # Severity: 0.2 pts (exact), 0.1 pts (adjacent)
        severity_order = ["P1", "P2", "P3"]
        if action.severity == gt["severity"]:
            score += 0.2
            parts.append("severity correct (+0.2)")
        elif abs(severity_order.index(action.severity) - severity_order.index(gt["severity"])) == 1:
            score += 0.1
            parts.append("severity off-by-one (+0.1)")
        else:
            parts.append(f"severity wrong (expected: {gt['severity']})")

        # Remediation: 0.3 pts (exact match only)
        if action.remediation == gt["remediation"]:
            score += 0.3
            parts.append("remediation correct (+0.3)")
        else:
            parts.append(f"remediation wrong (expected: {gt['remediation']})")

        # Summary: 0.1 pts for relevant, 0.05 for generic
        root_keyword = gt["root_cause"].split("-")[0]
        if action.summary and 10 <= len(action.summary) <= 120:
            if root_keyword in action.summary.lower():
                score += 0.1
                parts.append("summary relevant (+0.1)")
            else:
                score += 0.05
                parts.append("summary generic (+0.05)")
        else:
            parts.append("summary missing or invalid (+0.0)")

        feedback = f"Score: {score:.2f} | " + " | ".join(parts)
        return round(score, 2), feedback

    @property
    def state(self) -> IncidentState:
        return self._state

    def _make_obs(self, scenario: dict, task: str, step: int, reward: float, done: bool, feedback: str) -> IncidentObservation:
        return IncidentObservation(
            step=step,
            task_name=task,
            scenario_id=scenario["id"],
            alerts=scenario.get("alerts", []),
            log_snippets=scenario.get("log_snippets", []),
            dependency_graph=scenario.get("dependency_graph", {}),
            recent_deployments=scenario.get("recent_deployments", []),
            task_description=scenario.get("task_description", ""),
            reward=reward,
            done=done,
            feedback=feedback,
        )
