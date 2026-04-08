try:
    from ..models import IncidentAction, IncidentObservation
    from .incident_triage_environment import IncidentTriageEnvironment
except ImportError:
    try:
        from models import IncidentAction, IncidentObservation
        from incident_triage_environment import IncidentTriageEnvironment
    except ImportError:
        from models import IncidentAction, IncidentObservation
        from server.incident_triage_environment import IncidentTriageEnvironment

import logging
from openenv.core.env_server import create_app

try:
    from .scenarios import ALL_SCENARIOS
except ImportError:
    try:
        from scenarios import ALL_SCENARIOS
    except ImportError:
        from server.scenarios import ALL_SCENARIOS

logging.basicConfig(level=logging.INFO)
logging.info(f"[incident_triage_env] ALL_SCENARIOS keys: {list(ALL_SCENARIOS.keys())}")

# Single shared instance — the framework calls env_factory() on every request
# and close() in a finally block. close() is overridden as a no-op so this
# singleton survives across reset/step/state calls and state is preserved.
_shared_env = IncidentTriageEnvironment()

app = create_app(
    lambda: _shared_env,
    IncidentAction,
    IncidentObservation,
    env_name="incident_triage_env",
)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
