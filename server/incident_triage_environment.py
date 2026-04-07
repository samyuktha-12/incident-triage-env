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

    Each episode runs through all scenarios for the selected task (easy/medium/hard).
    One action per scenario — the episode ends when all scenarios are exhausted.
    Reward is shaped across 4 components per incident (root_cause, severity, remediation, summary).
    """

    def __init__(self, task_name: str = "easy"):
        super().__init__()
        self.task_name = task_name
        self._state = IncidentState()
        self._scenarios = []
        self._current_scenario = None
        self._scenario_index = 0

    def reset(self, **kwargs) -> IncidentObservation:
        task = kwargs.get("task", self.task_name)
        self.task_name = task
        self._scenarios = list(ALL_SCENARIOS[task])
        self._scenario_index = 0
        self._current_scenario = self._scenarios[self._scenario_index]
        self._state = IncidentState(
            episode_id=str(uuid.uuid4()),
            task_name=task,
            scenario_id=self._current_scenario["id"],
        )
        return self._make_observation(reward=0.0, done=False, feedback="Incident detected. Begin triage.")

    def step(self, action: IncidentAction) -> IncidentObservation:
        self._state.step_count += 1
        reward, feedback = self._grade(action)
        self._state.total_reward += reward

        self._scenario_index += 1
        done = self._scenario_index >= len(self._scenarios)

        if not done:
            self._current_scenario = self._scenarios[self._scenario_index]
            self._state.scenario_id = self._current_scenario["id"]
        else:
            self._state.solved = reward >= 0.7

        return self._make_observation(reward=reward, done=done, feedback=feedback)

    def _grade(self, action: IncidentAction) -> tuple:
        gt = self._current_scenario["ground_truth"]
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

    def _make_observation(self, reward: float, done: bool, feedback: str) -> IncidentObservation:
        s = self._current_scenario if self._current_scenario else {}
        return IncidentObservation(
            step=self._state.step_count,
            alerts=s.get("alerts", []),
            log_snippets=s.get("log_snippets", []),
            dependency_graph=s.get("dependency_graph", {}),
            recent_deployments=s.get("recent_deployments", []),
            task_description=s.get("task_description", ""),
            reward=reward,
            done=done,
            feedback=feedback,
        )
