"""
Tower Defense RL — HTTP Client

This is what YOUR TRAINING CODE imports.
Never touch raw HTTP — just call reset(), step(), state().

Usage:
    from envs.tower_defense.client import TowerDefenseEnv
    from envs.tower_defense.models import TowerDefenseAction

    env = TowerDefenseEnv(base_url="http://localhost:8000")
    result = env.reset(difficulty="easy")

    while not result.done:
        action = TowerDefenseAction(place_tower=True, row=1, col=2, tower_type="arrow")
        result = env.step(action)
        print(f"Reward: {result.reward}  |  Base HP: {result.observation.base_hp}")
"""

from typing import Any, Dict

from core.http_env_client import HTTPEnvClient, StepResult
from envs.tower_defense.models import (
    TowerDefenseAction,
    TowerDefenseObservation,
    TowerDefenseState,
)


class TowerDefenseEnv(HTTPEnvClient[TowerDefenseAction, TowerDefenseObservation]):
    """
    HTTP client for the Tower Defense RL environment.
    Follows the OpenEnv standard — all communication via HTTP/JSON.
    """

    def reset(self, difficulty: str = "easy") -> StepResult:
        """Start a new episode at the given difficulty."""
        import requests
        resp = requests.post(
            f"{self.base_url}/reset",
            json={"difficulty": difficulty},
            timeout=10,
        )
        resp.raise_for_status()
        return self._parse_result(resp.json())

    def grade(self) -> Dict[str, Any]:
        """Fetch the automated grading report for the current episode."""
        import requests
        resp = requests.get(f"{self.base_url}/grade", timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ---------------------------------------------------------------- #
    # Required overrides                                                #
    # ---------------------------------------------------------------- #

    def _step_payload(self, action: TowerDefenseAction) -> Dict[str, Any]:
        """Convert typed action → JSON dict."""
        return {
            "place_tower": action.place_tower,
            "row": action.row,
            "col": action.col,
            "tower_type": action.tower_type,
        }

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult:
        """Parse JSON response → typed StepResult."""
        obs = TowerDefenseObservation(
            grid=payload.get("grid", []),
            enemy_count=payload.get("enemy_count", 0),
            base_hp=payload.get("base_hp", 100),
            gold=payload.get("gold", 200),
            wave_number=payload.get("wave_number", 1),
            total_waves=payload.get("total_waves", 3),
            enemies_killed_this_wave=payload.get("enemies_killed_this_wave", 0),
            enemies_leaked_this_wave=payload.get("enemies_leaked_this_wave", 0),
            legal_cells=payload.get("legal_cells", []),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
        )
        return StepResult(
            observation=obs,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> TowerDefenseState:
        """Parse JSON response → typed State."""
        return TowerDefenseState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            difficulty=payload.get("difficulty", "easy"),
            grid_size=payload.get("grid_size", 4),
            total_waves=payload.get("total_waves", 3),
            current_wave=payload.get("current_wave", 1),
            total_reward=payload.get("total_reward", 0.0),
            towers_placed=payload.get("towers_placed", 0),
            total_kills=payload.get("total_kills", 0),
            total_leaks=payload.get("total_leaks", 0),
            game_won=payload.get("game_won", False),
            game_lost=payload.get("game_lost", False),
        )
