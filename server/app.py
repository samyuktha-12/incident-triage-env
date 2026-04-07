try:
    from ..models import IncidentAction, IncidentObservation
    from .incident_triage_environment import IncidentTriageEnvironment
except ImportError:
    from models import IncidentAction, IncidentObservation
    from incident_triage_environment import IncidentTriageEnvironment

from openenv.core.env_server import create_app

app = create_app(
    IncidentTriageEnvironment,
    IncidentAction,
    IncidentObservation,
    env_name="incident_triage_env",
)
