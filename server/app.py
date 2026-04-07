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

from openenv.core.env_server import create_app

app = create_app(
    IncidentTriageEnvironment,
    IncidentAction,
    IncidentObservation,
    env_name="incident_triage_env",
)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
