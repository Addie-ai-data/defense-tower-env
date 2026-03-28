"""
Tower Defense RL Environment — Type-safe models.

These are the CONTRACTS between your training code and the environment.
Your IDE autocompletes every field. Typos are caught before running.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.env_server import Action, Observation, State


# ------------------------------------------------------------------ #
# Tower types available in the game                                   #
# ------------------------------------------------------------------ #

TOWER_TYPES = {
    "arrow": {
        "name": "Arrow Tower",
        "damage": 10,
        "range": 2,
        "cost": 50,
        "description": "Basic single-target tower. Available from level 1.",
    },
    "cannon": {
        "name": "Cannon Tower",
        "damage": 25,
        "range": 1,
        "cost": 100,
        "description": "High damage, short range. Available from level 2.",
    },
    "magic": {
        "name": "Magic Tower",
        "damage": 15,
        "range": 3,
        "cost": 150,
        "description": "Long range, hits all enemies in range. Available from level 3.",
    },
}

# ------------------------------------------------------------------ #
# Action                                                              #
# ------------------------------------------------------------------ #

@dataclass
class TowerDefenseAction(Action):
    """
    What the AI agent can do each turn.

    place_tower=True  → place a tower at (row, col) of tower_type
    place_tower=False → pass (skip this turn, save gold)
    """
    place_tower: bool = False          # True = place, False = pass
    row: int = 0                       # Grid row (0-indexed)
    col: int = 0                       # Grid column (0-indexed)
    tower_type: str = "arrow"          # One of: "arrow", "cannon", "magic"
    metadata: Dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------ #
# Observation                                                         #
# ------------------------------------------------------------------ #

@dataclass
class TowerDefenseObservation(Observation):
    """
    What the AI agent sees after each action.

    grid         : flattened NxN grid
                   0 = empty, 1 = path, 2 = arrow tower,
                   3 = cannon tower, 4 = magic tower
    enemy_count  : number of enemies currently on the grid
    base_hp      : base health remaining (game over at 0)
    gold         : currency available to place towers
    wave_number  : current wave (1-indexed)
    total_waves  : total waves in this level
    enemies_killed_this_wave : enemies killed so far this wave
    enemies_leaked_this_wave : enemies that reached the base this wave
    legal_cells  : list of (row, col) pairs where towers CAN be placed
    """
    grid: List[int] = field(default_factory=list)
    enemy_count: int = 0
    base_hp: int = 100
    gold: int = 200
    wave_number: int = 1
    total_waves: int = 3
    enemies_killed_this_wave: int = 0
    enemies_leaked_this_wave: int = 0
    legal_cells: List[List[int]] = field(default_factory=list)
    done: bool = False
    reward: Optional[float] = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------ #
# State                                                               #
# ------------------------------------------------------------------ #

@dataclass
class TowerDefenseState(State):
    """Episode metadata — useful for logging and debugging."""
    episode_id: Optional[str] = None
    step_count: int = 0
    difficulty: str = "easy"          # "easy", "medium", "hard"
    grid_size: int = 4                # 4, 6, or 8
    total_waves: int = 3
    current_wave: int = 1
    total_reward: float = 0.0
    towers_placed: int = 0
    total_kills: int = 0
    total_leaks: int = 0
    game_won: bool = False
    game_lost: bool = False
