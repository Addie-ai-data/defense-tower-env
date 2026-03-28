"""
OpenEnv Core — HTTP client base class.
Your training code imports this and never sees raw HTTP.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, TypeVar

import requests

from core.env_server import Action, Observation, State

ActionT = TypeVar("ActionT", bound=Action)
ObsT = TypeVar("ObsT", bound=Observation)


@dataclass
class StepResult(Generic[ObsT]):
    """Returned by every reset() and step() call."""
    observation: ObsT
    reward: float
    done: bool


class HTTPEnvClient(ABC, Generic[ActionT, ObsT]):
    """
    Base HTTP client for all OpenEnv environments.

    Subclasses implement:
      _step_payload()  — convert typed Action → JSON dict
      _parse_result()  — convert JSON response → StepResult
      _parse_state()   — convert JSON response → State
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------ #
    # Public API — your training loop calls these                         #
    # ------------------------------------------------------------------ #

    def reset(self, **kwargs) -> StepResult:
        """Start a new episode. Returns first observation."""
        resp = requests.post(f"{self.base_url}/reset", json=kwargs, timeout=10)
        resp.raise_for_status()
        return self._parse_result(resp.json())

    def step(self, action: ActionT) -> StepResult:
        """Send an action, receive the next observation + reward."""
        payload = self._step_payload(action)
        resp = requests.post(f"{self.base_url}/step", json=payload, timeout=10)
        resp.raise_for_status()
        return self._parse_result(resp.json())

    def state(self) -> State:
        """Fetch current episode metadata."""
        resp = requests.get(f"{self.base_url}/state", timeout=10)
        resp.raise_for_status()
        return self._parse_state(resp.json())

    def health(self) -> Dict[str, Any]:
        """Check server is alive."""
        resp = requests.get(f"{self.base_url}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    # Subclass hooks                                                       #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def _step_payload(self, action: ActionT) -> Dict[str, Any]:
        """Convert typed action to JSON dict for HTTP POST."""

    @abstractmethod
    def _parse_result(self, payload: Dict[str, Any]) -> StepResult:
        """Parse JSON response into a typed StepResult."""

    @abstractmethod
    def _parse_state(self, payload: Dict[str, Any]) -> State:
        """Parse JSON response into a typed State."""
