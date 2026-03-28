"""
Tower Defense RL Environment — Game logic + Automated Grader.

This is the ENVIRONMENT the AI agent learns to play.
It runs inside the FastAPI server (Docker container).

Three difficulty levels:
  easy   — 4x4 grid, 1 path, 1 tower type, 3 waves
  medium — 6x6 grid, 2 paths, 2 tower types, 5 waves
  hard   — 8x8 grid, 3 paths, 3 tower types, 10 waves
"""

import os
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple

from envs.tower_defense.models import (
    TowerDefenseAction,
    TowerDefenseObservation,
    TowerDefenseState,
    TOWER_TYPES,
)


# ------------------------------------------------------------------ #
# Level configurations                                                #
# ------------------------------------------------------------------ #

LEVEL_CONFIG = {
    "easy": {
        "grid_size": 4,
        "total_waves": 3,
        "enemies_per_wave": 5,
        "enemy_hp": 30,
        "enemy_speed": 1,
        "start_gold": 200,
        "gold_per_kill": 20,
        "base_hp": 100,
        "allowed_towers": ["arrow"],
        "num_paths": 1,
    },
    "medium": {
        "grid_size": 6,
        "total_waves": 5,
        "enemies_per_wave": 8,
        "enemy_hp": 50,
        "enemy_speed": 1,
        "start_gold": 300,
        "gold_per_kill": 25,
        "base_hp": 150,
        "allowed_towers": ["arrow", "cannon"],
        "num_paths": 2,
    },
    "hard": {
        "grid_size": 8,
        "total_waves": 10,
        "enemies_per_wave": 12,
        "enemy_hp": 80,
        "enemy_speed": 2,
        "start_gold": 400,
        "gold_per_kill": 30,
        "base_hp": 200,
        "allowed_towers": ["arrow", "cannon", "magic"],
        "num_paths": 3,
    },
}

# Grid cell codes
EMPTY = 0
PATH = 1
TOWER_ARROW = 2
TOWER_CANNON = 3
TOWER_MAGIC = 4

TOWER_CODE = {"arrow": TOWER_ARROW, "cannon": TOWER_CANNON, "magic": TOWER_MAGIC}


# ------------------------------------------------------------------ #
# Path generator                                                      #
# ------------------------------------------------------------------ #

def _generate_path(grid_size: int, seed: int = 42) -> List[Tuple[int, int]]:
    """
    Generate a snaking path from left edge to right edge that
    passes through the MIDDLE rows so towers have room to cover it.
    Returns list of (row, col) cells.
    """
    rng = random.Random(seed)
    path = []
    # Start in the middle third so there's room above AND below for towers
    mid = grid_size // 2
    row = rng.randint(max(1, mid - 1), min(grid_size - 2, mid + 1))
    col = 0
    path.append((row, col))

    while col < grid_size - 1:
        # Snake up or down occasionally, but stay away from edges
        if rng.random() < 0.5:
            direction = rng.choice([-1, 1])
            new_row = row + direction
            # Keep path in rows 1..(n-2) so towers always have adjacent empty cells
            if 1 <= new_row <= grid_size - 2:
                row = new_row
                path.append((row, col))
        col += 1
        path.append((row, col))

    # Deduplicate while preserving order
    seen = set()
    unique_path = []
    for cell in path:
        if cell not in seen:
            seen.add(cell)
            unique_path.append(cell)
    return unique_path


# ------------------------------------------------------------------ #
# Enemy                                                               #
# ------------------------------------------------------------------ #

class Enemy:
    def __init__(self, hp: int, path: List[Tuple[int, int]]):
        self.hp = hp
        self.max_hp = hp
        self.path = path
        self.path_index = 0          # Current position on path
        self.alive = True
        self.reached_base = False

    @property
    def position(self) -> Optional[Tuple[int, int]]:
        if self.path_index < len(self.path):
            return self.path[self.path_index]
        return None

    def advance(self, speed: int = 1):
        """Move along the path."""
        self.path_index += speed
        if self.path_index >= len(self.path):
            self.reached_base = True
            self.alive = False

    def take_damage(self, dmg: int):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False


# ------------------------------------------------------------------ #
# Tower Defense Environment                                           #
# ------------------------------------------------------------------ #

class TowerDefenseEnvironment:
    """
    Full Tower Defense game environment.

    Episode structure:
      1. Agent places towers (placement phase)
      2. Wave of enemies advances along paths
      3. Towers fire at enemies in range
      4. Grader calculates reward
      5. Repeat for all waves
      6. Episode ends: all waves done OR base_hp <= 0
    """

    def __init__(self, difficulty: Optional[str] = None):
        self.difficulty = difficulty or os.getenv("TD_DIFFICULTY", "easy")
        assert self.difficulty in LEVEL_CONFIG, (
            f"difficulty must be one of {list(LEVEL_CONFIG)}"
        )
        self.cfg = LEVEL_CONFIG[self.difficulty]
        self._state: Optional[TowerDefenseState] = None
        self._grid: List[List[int]] = []
        self._paths: List[List[Tuple[int, int]]] = []
        self._enemies: List[Enemy] = []
        self._towers: List[Dict[str, Any]] = []
        self._episode_id: str = ""
        self._step_count: int = 0
        self._gold: int = 0
        self._base_hp: int = 0
        self._current_wave: int = 1
        self._kills: int = 0
        self._leaks: int = 0
        self._wave_kills: int = 0
        self._wave_leaks: int = 0
        self._total_reward: float = 0.0
        self._placement_phase: bool = True  # True = place towers, False = wave running
        self._visible_enemy_count: int = 0
        self._waves_completed: int = 0
        self._episode_done: bool = False
        self._game_won: bool = False
        self._game_lost: bool = False

    # ---------------------------------------------------------------- #
    # Public interface                                                  #
    # ---------------------------------------------------------------- #

    def reset(self) -> TowerDefenseObservation:
        """Start a new episode."""
        cfg = self.cfg
        n = cfg["grid_size"]

        self._episode_id = str(uuid.uuid4())[:8]
        self._step_count = 0
        self._gold = cfg["start_gold"]
        self._base_hp = cfg["base_hp"]
        self._current_wave = 1
        self._kills = 0
        self._leaks = 0
        self._wave_kills = 0
        self._wave_leaks = 0
        self._total_reward = 0.0
        self._placement_phase = True
        self._towers = []
        self._enemies = []
        self._visible_enemy_count = 0
        self._waves_completed = 0
        self._episode_done = False
        self._game_won = False
        self._game_lost = False

        # Build empty grid
        self._grid = [[EMPTY] * n for _ in range(n)]

        # Generate paths and mark them on grid
        self._paths = []
        for i in range(cfg["num_paths"]):
            path = _generate_path(n, seed=42 + i * 7)
            self._paths.append(path)
            for (r, c) in path:
                self._grid[r][c] = PATH

        self._update_state()
        return self._make_observation(reward=0.0, done=False)

    def step(self, action: TowerDefenseAction) -> TowerDefenseObservation:
        """
        Process one action.

        During placement phase: place a tower or pass.
        Passing (or after placement) triggers the wave simulation.
        """
        if self._episode_done:
            self._update_state()
            return self._make_observation(reward=0.0, done=True)

        self._step_count += 1
        reward = 0.0
        done = False

        if self._placement_phase:
            reward += self._handle_placement(action)
            # Trigger the wave after every step (simplified: agent places one tower per wave)
            wave_reward, done = self._simulate_wave()
            reward += wave_reward
        else:
            # Should not normally reach here, but handle gracefully
            pass

        self._total_reward += reward
        self._update_state()

        return self._make_observation(reward=reward, done=done)

    @property
    def state(self) -> TowerDefenseState:
        self._update_state()
        return self._state

    # ---------------------------------------------------------------- #
    # Placement phase                                                   #
    # ---------------------------------------------------------------- #

    def _handle_placement(self, action: TowerDefenseAction) -> float:
        """Try to place a tower. Returns placement reward/penalty."""
        if not action.place_tower:
            return 0.0   # Pass — no penalty, saves gold

        r, c = action.row, action.col
        t = action.tower_type
        n = self.cfg["grid_size"]

        # Validate tower type for this difficulty
        if t not in self.cfg["allowed_towers"]:
            return -2.0   # Penalty: tried illegal tower type

        tower_info = TOWER_TYPES[t]
        cost = tower_info["cost"]

        # Validate position
        if not (0 <= r < n and 0 <= c < n):
            return -2.0   # Out of bounds

        if self._grid[r][c] != EMPTY:
            return -2.0   # Cell is path or already has tower

        # Check gold
        if self._gold < cost:
            return -1.0   # Can't afford it

        # Place tower
        self._grid[r][c] = TOWER_CODE[t]
        self._towers.append({"row": r, "col": c, "type": t})
        self._gold -= cost

        return -1.0   # Small cost for placing (encourages efficiency)

    # ---------------------------------------------------------------- #
    # Wave simulation                                                   #
    # ---------------------------------------------------------------- #

    def _simulate_wave(self) -> Tuple[float, bool]:
        """
        Run a full wave tick-by-tick.
        Enemies are staggered (one enters per 2 ticks) so the path is
        never instantly flooded — well-placed towers can actually catch them.
        Returns (wave_reward, episode_done).
        """
        cfg = self.cfg
        wave_reward = 0.0
        self._wave_kills = 0
        self._wave_leaks = 0
        self._placement_phase = False
        self._visible_enemy_count = 0

        # Build all enemies with staggered spawn ticks
        enemy_queue: List[Dict] = []
        idx = 0
        for path in self._paths:
            for _ in range(cfg["enemies_per_wave"]):
                enemy_queue.append({
                    "hp": cfg["enemy_hp"],
                    "path_idx": 0,
                    "path": path,
                    "alive": True,
                    "reached_base": False,
                    "spawn_tick": idx * 2,
                })
                idx += 1

        path_len = max(len(p) for p in self._paths)
        max_ticks = path_len + len(enemy_queue) * 2 + 10
        killed = 0
        leaked = 0

        for tick in range(max_ticks):
            active = [
                e for e in enemy_queue
                if tick >= e["spawn_tick"] and e["alive"]
            ]
            self._visible_enemy_count = len(active)

            # Each tower fires once per tick
            for tower in self._towers:
                tr, tc = tower["row"], tower["col"]
                t_type = tower["type"]
                t_info = TOWER_TYPES[t_type]
                dmg = t_info["damage"]
                t_range = t_info["range"]

                if t_type == "magic":
                    for e in active:
                        if not e["alive"]:
                            continue
                        er, ec = e["path"][e["path_idx"]]
                        if abs(er - tr) + abs(ec - tc) <= t_range:
                            e["hp"] -= dmg
                            if e["hp"] <= 0:
                                e["alive"] = False
                else:
                    # Hit the furthest-along enemy in range first
                    targets = sorted(
                        [e for e in active if e["alive"]],
                        key=lambda e: -e["path_idx"],
                    )
                    for e in targets:
                        er, ec = e["path"][e["path_idx"]]
                        if abs(er - tr) + abs(ec - tc) <= t_range:
                            e["hp"] -= dmg
                            if e["hp"] <= 0:
                                e["alive"] = False
                            break

            # Advance alive enemies
            for e in active:
                if not e["alive"]:
                    continue
                e["path_idx"] += cfg["enemy_speed"]
                if e["path_idx"] >= len(e["path"]):
                    e["reached_base"] = True
                    e["alive"] = False

            # Early exit once every spawned enemy is resolved
            spawned = [e for e in enemy_queue if tick >= e["spawn_tick"]]
            if spawned and all(not e["alive"] for e in spawned):
                unspawned = [e for e in enemy_queue if tick < e["spawn_tick"]]
                if not unspawned:
                    break

        self._visible_enemy_count = 0

        # Tally results
        for e in enemy_queue:
            if e["reached_base"]:
                leaked += 1
                self._wave_leaks += 1
                self._leaks += 1
                wave_reward += self._grader_leak_penalty()
                self._base_hp -= 10
            elif not e["alive"] and e["hp"] <= 0:
                killed += 1
                self._wave_kills += 1
                self._kills += 1
                wave_reward += self._grader_kill_reward()
                self._gold += cfg["gold_per_kill"]

        # Wave clear bonus
        if killed > 0 and leaked == 0:
            wave_reward += self._grader_wave_clear_bonus()

        self._waves_completed += 1

        # Check episode end
        done = False
        if self._base_hp <= 0:
            self._episode_done = True
            self._game_won = False
            self._game_lost = True
            done = True   # Lost
        elif self._current_wave >= cfg["total_waves"]:
            wave_reward += self._grader_win_bonus()
            self._episode_done = True
            self._game_won = True
            self._game_lost = False
            done = True   # Won
        else:
            self._current_wave += 1
            self._placement_phase = True   # Open next placement phase
            self._episode_done = False
            self._game_won = False
            self._game_lost = False

        return wave_reward, done

    # ---------------------------------------------------------------- #
    # GRADER — reward logic (evaluation criterion)                     #
    # ---------------------------------------------------------------- #

    def _grader_kill_reward(self) -> float:
        """
        +10 per enemy killed.
        Justification: directly measures task completion (blocking enemies).
        """
        return 10.0

    def _grader_leak_penalty(self) -> float:
        """
        -5 per enemy that reaches the base.
        Justification: every leak damages base HP; agent must learn to prevent this.
        """
        return -5.0

    def _grader_wave_clear_bonus(self) -> float:
        """
        +20 for clearing a wave with zero leaks.
        Justification: rewards perfect defence strategy.
        """
        return 20.0

    def _grader_win_bonus(self) -> float:
        """
        +50 if the agent wins (survives all waves).
        Scaled by remaining HP to reward efficient play.
        """
        hp_fraction = self._base_hp / self.cfg["base_hp"]
        return 50.0 + (50.0 * hp_fraction)

    def grade_episode(self) -> Dict[str, Any]:
        """
        Automated grader — returns full evaluation report.
        Called externally to score a completed episode.
        """
        cfg = self.cfg
        total_possible_kills = (
            cfg["enemies_per_wave"] * cfg["total_waves"] * cfg["num_paths"]
        )
        kill_rate = self._kills / max(total_possible_kills, 1)
        game_won = self._game_won

        return {
            "episode_id": self._episode_id,
            "difficulty": self.difficulty,
            "game_won": game_won,
            "total_reward": round(self._total_reward, 2),
            "kills": self._kills,
            "leaks": self._leaks,
            "kill_rate": round(kill_rate, 3),
            "base_hp_remaining": self._base_hp,
            "towers_placed": len(self._towers),
            "waves_completed": self._waves_completed,
            "total_waves": cfg["total_waves"],
            "score": self._compute_score(game_won, kill_rate),
        }

    def _compute_score(self, won: bool, kill_rate: float) -> int:
        """
        Final numeric score for the episode (0-100).
        Used by automated evaluation system.
        """
        base = int(kill_rate * 60)          # Up to 60 pts for kills
        hp_bonus = int((self._base_hp / self.cfg["base_hp"]) * 20)   # Up to 20 pts
        win_bonus = 20 if won else 0         # 20 pts for winning
        efficiency = max(0, 10 - len(self._towers))  # Bonus for using fewer towers
        return min(100, base + hp_bonus + win_bonus + efficiency)

    # ---------------------------------------------------------------- #
    # Helpers                                                           #
    # ---------------------------------------------------------------- #

    def _legal_cells(self) -> List[List[int]]:
        """Return all (row, col) cells where a tower can be placed."""
        cells = []
        n = self.cfg["grid_size"]
        for r in range(n):
            for c in range(n):
                if self._grid[r][c] == EMPTY:
                    cells.append([r, c])
        return cells

    def _make_observation(self, reward: float, done: bool) -> TowerDefenseObservation:
        flat_grid = [cell for row in self._grid for cell in row]
        return TowerDefenseObservation(
            grid=flat_grid,
            enemy_count=self._visible_enemy_count,
            base_hp=self._base_hp,
            gold=self._gold,
            wave_number=self._current_wave,
            total_waves=self.cfg["total_waves"],
            enemies_killed_this_wave=self._wave_kills,
            enemies_leaked_this_wave=self._wave_leaks,
            legal_cells=self._legal_cells(),
            done=done,
            reward=reward,
        )

    def _update_state(self):
        self._state = TowerDefenseState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            difficulty=self.difficulty,
            grid_size=self.cfg["grid_size"],
            total_waves=self.cfg["total_waves"],
            current_wave=self._current_wave,
            total_reward=self._total_reward,
            towers_placed=len(self._towers),
            total_kills=self._kills,
            total_leaks=self._leaks,
            game_won=self._game_won,
            game_lost=self._game_lost,
        )
