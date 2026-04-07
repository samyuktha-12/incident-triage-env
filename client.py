try:
    from openenv.core import EnvClient
except ImportError:
    from openenv.core.client import EnvClient


class IncidentTriageEnv(EnvClient):
    """HTTP client for the Incident Triage environment."""
    pass
