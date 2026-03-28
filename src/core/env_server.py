"""
OpenEnv Core — Abstract base classes.
Every environment MUST inherit from these.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Action(ABC):
    """Base class for all actions sent TO the environment."""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Observation(ABC):
    """Base class for all observations returned FROM the environment."""
    done: bool = False
    reward: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class State(ABC):
    """Base class for episode metadata."""
    episode_id: Optional[str] = None
    step_count: int = 0
