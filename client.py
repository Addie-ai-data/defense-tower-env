from __future__ import annotations

from typing import Any

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

try:
    from .models import SupportTriageAction, SupportTriageObservation, SupportTriageState
except ImportError:
    from models import SupportTriageAction, SupportTriageObservation, SupportTriageState


class SupportTriageEnv(
    EnvClient[SupportTriageAction, SupportTriageObservation, SupportTriageState]
):
    def _step_payload(self, action: SupportTriageAction) -> dict[str, Any]:
        return action.model_dump(mode="json", exclude_none=True)

    def _parse_result(self, payload: dict[str, Any]) -> StepResult[SupportTriageObservation]:
        observation_payload = payload.get("observation", payload)
        observation = SupportTriageObservation.model_validate(observation_payload)
        reward = payload.get("reward", observation.reward or 0.0)
        done = payload.get("done", observation.done)
        return StepResult(observation=observation, reward=reward, done=done)

    def _parse_state(self, payload: dict[str, Any]) -> SupportTriageState:
        return SupportTriageState.model_validate(payload)
