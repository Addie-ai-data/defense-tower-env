"""
Baseline inference entrypoint for the Tower Defense environment.

This script provides:
  - a reusable greedy policy via predict()/act()
  - a local smoke test against the in-process environment
  - optional HTTP mode against a running OpenEnv server
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import requests

from envs.tower_defense.models import TowerDefenseAction, TowerDefenseObservation
from envs.tower_defense.server.environment import TOWER_TYPES, TowerDefenseEnvironment

VALID_DIFFICULTIES = ("easy", "medium", "hard")


def _coerce_observation(payload: dict[str, Any] | TowerDefenseObservation) -> TowerDefenseObservation:
    if isinstance(payload, TowerDefenseObservation):
        return payload
    return TowerDefenseObservation(
        grid=payload.get("grid", []),
        enemy_count=payload.get("enemy_count", 0),
        base_hp=payload.get("base_hp", 100),
        gold=payload.get("gold", 0),
        wave_number=payload.get("wave_number", 1),
        total_waves=payload.get("total_waves", 1),
        enemies_killed_this_wave=payload.get("enemies_killed_this_wave", 0),
        enemies_leaked_this_wave=payload.get("enemies_leaked_this_wave", 0),
        legal_cells=payload.get("legal_cells", []),
        done=payload.get("done", False),
        reward=payload.get("reward", 0.0),
        metadata=payload.get("metadata", {}),
    )


def _allowed_towers(obs: TowerDefenseObservation, difficulty: str) -> list[str]:
    if difficulty == "hard":
        ordered = ["magic", "cannon", "arrow"]
    elif difficulty == "medium":
        ordered = ["cannon", "arrow"]
    else:
        ordered = ["arrow"]
    return [tower for tower in ordered if obs.gold >= TOWER_TYPES[tower]["cost"]]


def _coverage_score(obs: TowerDefenseObservation, row: int, col: int, tower_type: str) -> tuple[int, int]:
    if not obs.grid:
        return (0, 0)

    size = int(len(obs.grid) ** 0.5)
    tower_range = TOWER_TYPES[tower_type]["range"]
    path_cells = 0
    weighted_path_distance = 0

    for index, cell in enumerate(obs.grid):
        if cell != 1:
            continue
        path_row, path_col = divmod(index, size)
        dist = abs(path_row - row) + abs(path_col - col)
        if dist <= tower_range:
            path_cells += 1
            weighted_path_distance += max(0, tower_range - dist + 1)

    return (path_cells, weighted_path_distance)


def choose_action(obs: dict[str, Any] | TowerDefenseObservation, difficulty: str = "easy") -> TowerDefenseAction:
    observation = _coerce_observation(obs)

    if observation.done or not observation.legal_cells:
        return TowerDefenseAction(place_tower=False)

    affordable = _allowed_towers(observation, difficulty)
    if not affordable:
        return TowerDefenseAction(place_tower=False)

    best_choice: tuple[tuple[int, int, int, int], TowerDefenseAction] | None = None
    for tower_type in affordable:
        tower_cost = TOWER_TYPES[tower_type]["cost"]
        tower_damage = TOWER_TYPES[tower_type]["damage"]
        for row, col in observation.legal_cells:
            coverage, weighted_distance = _coverage_score(observation, row, col, tower_type)
            if coverage == 0:
                continue
            rank = (coverage, weighted_distance, tower_damage, -tower_cost)
            action = TowerDefenseAction(
                place_tower=True,
                row=row,
                col=col,
                tower_type=tower_type,
            )
            if best_choice is None or rank > best_choice[0]:
                best_choice = (rank, action)

    if best_choice is None:
        return TowerDefenseAction(place_tower=False)
    return best_choice[1]


def predict(observation: dict[str, Any] | TowerDefenseObservation, difficulty: str = "easy") -> dict[str, Any]:
    action = choose_action(observation, difficulty=difficulty)
    return {
        "place_tower": action.place_tower,
        "row": action.row,
        "col": action.col,
        "tower_type": action.tower_type,
    }


def act(observation: dict[str, Any] | TowerDefenseObservation, difficulty: str = "easy") -> dict[str, Any]:
    return predict(observation, difficulty=difficulty)


def run_local_episode(difficulty: str) -> dict[str, Any]:
    env = TowerDefenseEnvironment(difficulty=difficulty)
    obs = env.reset()

    while not obs.done:
        action = choose_action(obs, difficulty=difficulty)
        obs = env.step(action)

    return env.grade_episode()


def run_http_episode(base_url: str, difficulty: str) -> dict[str, Any]:
    reset_resp = requests.post(
        f"{base_url.rstrip('/')}/reset",
        json={"difficulty": difficulty},
        timeout=15,
    )
    reset_resp.raise_for_status()
    obs = reset_resp.json()

    while not obs.get("done", False):
        action = predict(obs, difficulty=difficulty)
        step_resp = requests.post(
            f"{base_url.rstrip('/')}/step",
            json=action,
            timeout=15,
        )
        step_resp.raise_for_status()
        obs = step_resp.json()

    grade_resp = requests.get(f"{base_url.rstrip('/')}/grade", timeout=15)
    grade_resp.raise_for_status()
    return grade_resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline Tower Defense inference.")
    parser.add_argument(
        "--difficulty",
        choices=VALID_DIFFICULTIES,
        default="easy",
        help="Episode difficulty to evaluate.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional OpenEnv server URL. If omitted, run locally in-process.",
    )
    args = parser.parse_args()

    if args.base_url:
        report = run_http_episode(args.base_url, args.difficulty)
    else:
        report = run_local_episode(args.difficulty)

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
