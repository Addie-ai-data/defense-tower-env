from openenv.core.env_server import create_app
import os

import uvicorn

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


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
