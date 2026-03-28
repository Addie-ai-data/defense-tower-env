from openenv.core.env_server import create_app

try:
    from ..models import SupportTriageAction, SupportTriageObservation
    from .support_triage_environment import SupportTriageEnvironment
except ImportError:
    from models import SupportTriageAction, SupportTriageObservation
    from server.support_triage_environment import SupportTriageEnvironment


def env_factory() -> SupportTriageEnvironment:
    return SupportTriageEnvironment()


app = create_app(
    env_factory,
    SupportTriageAction,
    SupportTriageObservation,
    env_name="support_triage_env",
    max_concurrent_envs=8,
)
