"""
Tower Defense RL — Policy Showdown Demo

Runs 4 policies across 3 difficulty levels.
Shows live gameplay, rewards, and a final leaderboard.

Run this after starting the server:
    # Terminal 1:
    uvicorn envs.tower_defense.server.app:app --host 0.0.0.0 --port 8000

    # Terminal 2:
    python demo.py
"""

import random
import sys
import time

import requests

# ------------------------------------------------------------------ #
# Inline environment (no server needed for demo)                      #
# ------------------------------------------------------------------ #

sys.path.insert(0, "./src")

from envs.tower_defense.server.environment import TowerDefenseEnvironment # type: ignore
from envs.tower_defense.models import TowerDefenseAction, TowerDefenseObservation # type: ignore


# ------------------------------------------------------------------ #
# Policies                                                            #
# ------------------------------------------------------------------ #

class RandomPolicy:
    """Randomly place towers on legal cells."""
    name = "🎲 Random"

    def select_action(self, obs: TowerDefenseObservation, difficulty: str) -> TowerDefenseAction:
        if obs.legal_cells and obs.gold >= 50:
            cell = random.choice(obs.legal_cells)
            return TowerDefenseAction(place_tower=True, row=cell[0], col=cell[1], tower_type="arrow")
        return TowerDefenseAction(place_tower=False)


class PassPolicy:
    """Never place any towers — worst possible strategy."""
    name = "🛑 Always Pass"

    def select_action(self, obs: TowerDefenseObservation, difficulty: str) -> TowerDefenseAction:
        return TowerDefenseAction(place_tower=False)


class GreedyPolicy:
    """
    Place towers in empty cells that cover the most path cells within range.
    Smarter than random — actually thinks about coverage and tower types.
    """
    name = "🧠 Greedy Placer"

    def select_action(self, obs: TowerDefenseObservation, difficulty: str) -> TowerDefenseAction:
        if not obs.legal_cells or obs.gold < 50:
            return TowerDefenseAction(place_tower=False)

        # Simple: place best affordable tower at first legal cell
        tower = "arrow"
        if obs.gold >= 100:
            tower = "cannon"
        if obs.gold >= 150:
            tower = "magic"
        row, col = obs.legal_cells[0]
        return TowerDefenseAction(
            place_tower=True, row=row, col=col, tower_type=tower
        )


class SmartPolicy:
    """
    Place towers near the start of enemy paths to block early.
    """
    name = "🛡️ Smart Blocker"

    def select_action(self, obs: TowerDefenseObservation, difficulty: str) -> TowerDefenseAction:
        if not obs.legal_cells or obs.gold < 50:
            return TowerDefenseAction(place_tower=False)

        n = int(len(obs.grid) ** 0.5)

        # Find path starts (top row with path)
        path_starts = []
        for c in range(n):
            if obs.grid[0 * n + c] == 1:  # Top row
                path_starts.append((0, c))
        if not path_starts:
            # If not top, perhaps left
            for r in range(n):
                if obs.grid[r * n + 0] == 1:
                    path_starts.append((r, 0))

        # Find legal cells near path starts
        near_starts = []
        for r, c in obs.legal_cells:
            for pr, pc in path_starts:
                if abs(r - pr) + abs(c - pc) <= 2:
                    near_starts.append((r, c))
                    break

        if near_starts:
            cell = random.choice(near_starts)  # Random among near
        else:
            cell = random.choice(obs.legal_cells)

        # Pick best affordable tower
        tower = "arrow"
        if obs.gold >= 100:
            tower = "cannon"
        if obs.gold >= 150:
            tower = "magic"

        return TowerDefenseAction(
            place_tower=True, row=cell[0], col=cell[1], tower_type=tower
        )
class EpsilonGreedyPolicy:
    """
    Simulates a learning agent: starts random, becomes greedy over time.
    """
    name = "📈 Epsilon-Greedy"

    def __init__(self):
        self.steps = 0
        self._greedy = GreedyPolicy()
        self._random = RandomPolicy()

    def select_action(self, obs: TowerDefenseObservation, difficulty: str) -> TowerDefenseAction:
        self.steps += 1
        epsilon = max(0.1, 1.0 - self.steps / 30)   # Decay over 30 steps
        if random.random() < epsilon:
            return self._random.select_action(obs, difficulty)
        return self._greedy.select_action(obs, difficulty)


# ------------------------------------------------------------------ #
# Grid visualizer                                                     #
# ------------------------------------------------------------------ #

CELL_DISPLAY = {
    0: "·",    # Empty
    1: "─",    # Path
    2: "A",    # Arrow tower
    3: "C",    # Cannon tower
    4: "M",    # Magic tower
}


def print_grid(grid, n):
    lines = []
    lines.append("  " + " ".join(str(c) for c in range(n)))
    for r in range(n):
        row = grid[r * n: (r + 1) * n]
        lines.append(f"{r} " + " ".join(CELL_DISPLAY.get(c, "?") for c in row))
    return "\n".join(lines)


def run_episode_with_grids(policy, difficulty: str) -> (dict, list): # type: ignore
    env = TowerDefenseEnvironment(difficulty=difficulty)
    result = env.reset()
    total_reward = 0.0
    grids = []

    n = env.cfg["grid_size"]
    grids.append(f"Initial grid ({n}x{n}):\n" + print_grid(result.grid, n))

    while not result.done:
        action = policy.select_action(result, difficulty)
        result = env.step(action)
        total_reward += result.reward or 0.0

        grids.append(f"Wave {result.wave_number}/{result.total_waves} | Kills: {result.enemies_killed_this_wave} | Leaks: {result.enemies_leaked_this_wave} | Base HP: {result.base_hp} | Reward: {result.reward:+.1f}\n" + print_grid(result.grid, n))

    return env.grade_episode(), grids


# ------------------------------------------------------------------ #
# Episode runner                                                      #
# ------------------------------------------------------------------ #

def run_episode(policy, difficulty: str, visualize: bool = False) -> dict:
    env = TowerDefenseEnvironment(difficulty=difficulty)
    result = env.reset()
    total_reward = 0.0

    if visualize:
        n = env.cfg["grid_size"]
        print(f"\n  Initial grid ({n}x{n}):")
        print_grid(result.grid, n)

    while not result.done:
        action = policy.select_action(result, difficulty)
        result = env.step(action)
        total_reward += result.reward or 0.0

        if visualize:
            print(f"\n  Wave {result.wave_number}/{result.total_waves}  "
                  f"| Kills: {result.enemies_killed_this_wave}  "
                  f"| Leaks: {result.enemies_leaked_this_wave}  "
                  f"| Base HP: {result.base_hp}  "
                  f"| Reward: {result.reward:+.1f}")
            print_grid(result.grid, n)

    return env.grade_episode()


# ------------------------------------------------------------------ #
# Main showdown                                                       #
# ------------------------------------------------------------------ #

def run_showdown_for_difficulty(difficulty: str):
    policies = [
        RandomPolicy(),
        PassPolicy(),
        GreedyPolicy(),
        EpsilonGreedyPolicy(),
    ]

    n_episodes = 5  # Balanced for speed and accuracy

    results = {}
    for policy in policies:
        if hasattr(policy, "steps"):
            policy.steps = 0   # Reset learning agent

        scores = []
        rewards = []
        wins = 0

        for _ in range(n_episodes):
            report = run_episode(policy, difficulty=difficulty)
            scores.append(report["score"])
            rewards.append(report["total_reward"])
            if report["game_won"]:
                wins += 1

        avg_score = sum(scores) / len(scores)
        avg_reward = sum(rewards) / len(rewards)
        win_rate = wins / n_episodes * 100

        results[policy.name] = {
            "avg_score": avg_score,
            "avg_reward": avg_reward,
            "win_rate": win_rate,
        }

    # Format output
    output = f"🎮 Difficulty: {difficulty.upper()}\n"
    output += "-" * 60 + "\n"
    for policy in policies:
        res = results[policy.name]
        bar = "█" * int(res["avg_score"] / 5)
        output += f"  {policy.name:22s} | Score: {res['avg_score']:5.1f}/100 [{bar:<20}] "
        output += f"| Win%: {res['win_rate']:4.0f}% | Reward: {res['avg_reward']:+7.1f}\n"

    return output


def run_showdown():
    policies = [
        RandomPolicy(),
        PassPolicy(),
        GreedyPolicy(),
        EpsilonGreedyPolicy(),
    ]

    difficulties = ["easy", "medium", "hard"]
    n_episodes = 10

    print("\n" + "=" * 70)
    print("  🏰 TOWER DEFENSE RL — POLICY SHOWDOWN")
    print("=" * 70)
    print(f"  {n_episodes} episodes per policy per difficulty\n")

    # --- Visualize one greedy episode first ---
    print("📺 Watch 1 episode (Greedy policy, easy mode):")
    print("-" * 50)
    run_episode(GreedyPolicy(), difficulty="easy", visualize=True)
    print("-" * 50)

    # --- Full competition ---
    results = {}
    for difficulty in difficulties:
        print(f"\n\n🎮 Difficulty: {difficulty.upper()}")
        print("-" * 60)
        diff_results = {}

        for policy in policies:
            if hasattr(policy, "steps"):
                policy.steps = 0   # Reset learning agent

            scores = []
            rewards = []
            wins = 0

            for _ in range(n_episodes):
                report = run_episode(policy, difficulty=difficulty)
                scores.append(report["score"])
                rewards.append(report["total_reward"])
                if report["game_won"]:
                    wins += 1

            avg_score = sum(scores) / len(scores)
            avg_reward = sum(rewards) / len(rewards)
            win_rate = wins / n_episodes * 100

            diff_results[policy.name] = {
                "avg_score": avg_score,
                "avg_reward": avg_reward,
                "win_rate": win_rate,
            }

            bar = "█" * int(avg_score / 5)
            print(f"  {policy.name:22s} | Score: {avg_score:5.1f}/100 [{bar:<20}] "
                  f"| Win%: {win_rate:4.0f}% | Reward: {avg_reward:+7.1f}")

        results[difficulty] = diff_results

    # --- Final leaderboard ---
    print("\n\n" + "=" * 70)
    print("  🏆 FINAL LEADERBOARD (avg score across all difficulties)")
    print("=" * 70)

    medals = ["🥇", "🥈", "🥉", "  "]
    policy_totals = {}
    for policy in policies:
        total = sum(
            results[d][policy.name]["avg_score"] for d in difficulties
        ) / len(difficulties)
        policy_totals[policy.name] = total

    ranked = sorted(policy_totals.items(), key=lambda x: x[1], reverse=True)
    for i, (name, score) in enumerate(ranked):
        print(f"  {medals[i]} {name:22s} → {score:.1f}/100 avg")

    print("\n" + "=" * 70)
    print("  📊 REWARD LOGIC SUMMARY")
    print("=" * 70)
    print("  +10  per enemy killed        (task completion)")
    print("   -5  per enemy reaching base (failure penalty)")
    print("  +20  wave cleared with 0 leaks (perfect play bonus)")
    print("  -1   per tower placed        (efficiency pressure)")
    print("  +50–100  game won            (scaled by HP remaining)")
    print("\n  🎓 This is RL: the agent learns to place towers strategically")
    print("     to MAXIMIZE cumulative reward across all waves.\n")


if __name__ == "__main__":
    run_showdown()
