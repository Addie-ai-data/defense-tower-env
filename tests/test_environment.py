"""
Tower Defense RL — Test Suite

Tests verify:
  1. Runtime correctness — no crashes
  2. Interface compliance — follows OpenEnv standard
  3. Task design — difficulty levels work correctly
  4. Grading logic — reward system behaves as expected

Run with:  python tests/test_environment.py
"""

import sys
sys.path.insert(0, "./src")

from envs.tower_defense.server.environment import TowerDefenseEnvironment # type: ignore
from envs.tower_defense.models import TowerDefenseAction, TowerDefenseObservation, TowerDefenseState # type: ignore

PASS = "✅"
FAIL = "❌"
results = []


def test(name: str, condition: bool, detail: str = ""):
    icon = PASS if condition else FAIL
    msg = f"  {icon}  {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results.append(condition)
    return condition


def run_tests():
    print("\n" + "=" * 60)
    print("  Tower Defense RL — Test Suite")
    print("=" * 60 + "\n")

    # ---------------------------------------------------------------- #
    # 1. Runtime correctness                                            #
    # ---------------------------------------------------------------- #
    print("── 1. Runtime correctness ──────────────────────────────────")

    try:
        env = TowerDefenseEnvironment(difficulty="easy")
        obs = env.reset()
        test("Environment instantiates without error", True)
        test("reset() returns TowerDefenseObservation", isinstance(obs, TowerDefenseObservation))
        test("Grid is not empty", len(obs.grid) > 0)
        test("Grid size matches difficulty (4x4=16 cells)", len(obs.grid) == 16)
        test("Base HP is positive", obs.base_hp > 0)
        test("Gold is positive", obs.gold > 0)
        test("Legal cells exist", len(obs.legal_cells) > 0)
        test("No enemies are visible before a wave starts", obs.enemy_count == 0)
        test("Not done at start", not obs.done)
    except Exception as e:
        test("Environment initialisation", False, str(e))

    # ---------------------------------------------------------------- #
    # 2. Interface compliance (OpenEnv standard)                        #
    # ---------------------------------------------------------------- #
    print("\n── 2. Interface compliance (OpenEnv standard) ──────────────")

    env = TowerDefenseEnvironment(difficulty="easy")
    obs = env.reset()

    # step() works
    try:
        action = TowerDefenseAction(place_tower=False)
        obs2 = env.step(action)
        test("step() returns TowerDefenseObservation", isinstance(obs2, TowerDefenseObservation))
        test("step() observation has reward field", obs2.reward is not None)
        test("step() observation has done field", isinstance(obs2.done, bool))
        test("Observation enemy_count matches wave-boundary state", obs2.enemy_count == 0)
    except Exception as e:
        test("step() executes without error", False, str(e))

    # state() works
    try:
        state = env.state
        test("state property returns TowerDefenseState", isinstance(state, TowerDefenseState))
        test("state.step_count increments", state.step_count == 1)
        test("state.difficulty is set", state.difficulty == "easy")
    except Exception as e:
        test("state property works", False, str(e))

    # Action fields
    test("TowerDefenseAction has place_tower field", hasattr(TowerDefenseAction, "__dataclass_fields__") and "place_tower" in TowerDefenseAction.__dataclass_fields__)
    test("TowerDefenseAction has tower_type field", "tower_type" in TowerDefenseAction.__dataclass_fields__)

    # Observation fields
    test("Observation has grid field", "grid" in TowerDefenseObservation.__dataclass_fields__)
    test("Observation has base_hp field", "base_hp" in TowerDefenseObservation.__dataclass_fields__)
    test("Observation has legal_cells field", "legal_cells" in TowerDefenseObservation.__dataclass_fields__)

    # ---------------------------------------------------------------- #
    # 3. Task design — 3 difficulty levels                              #
    # ---------------------------------------------------------------- #
    print("\n── 3. Task design (3 difficulty levels) ────────────────────")

    for diff, expected_size, expected_waves in [
        ("easy",   4,  3),
        ("medium", 6,  5),
        ("hard",   8, 10),
    ]:
        env = TowerDefenseEnvironment(difficulty=diff)
        obs = env.reset()
        n = int(len(obs.grid) ** 0.5)
        test(
            f"{diff.capitalize()} — grid size {expected_size}x{expected_size}",
            n == expected_size,
            f"got {n}",
        )
        test(
            f"{diff.capitalize()} — {expected_waves} waves",
            obs.total_waves == expected_waves,
            f"got {obs.total_waves}",
        )

    # Tower restrictions
    env_easy = TowerDefenseEnvironment(difficulty="easy")
    env_easy.reset()
    action_cannon = TowerDefenseAction(place_tower=True, row=0, col=0, tower_type="cannon")
    obs_after = env_easy.step(action_cannon)
    # Cannon is not allowed in easy, should get a negative reward
    test(
        "Easy mode rejects cannon tower (negative reward)",
        (obs_after.reward is not None and obs_after.reward <= 0),
    )

    env_bounds = TowerDefenseEnvironment(difficulty="easy")
    env_bounds.reset()
    obs_oob = env_bounds.step(TowerDefenseAction(place_tower=True, row=99, col=99, tower_type="arrow"))
    test(
        "Out-of-bounds placement gets a penalty",
        (obs_oob.reward is not None and obs_oob.reward <= 0),
    )

    env_path = TowerDefenseEnvironment(difficulty="easy")
    obs_path_start = env_path.reset()
    path_index = obs_path_start.grid.index(1)
    path_row, path_col = divmod(path_index, env_path.cfg["grid_size"])
    obs_on_path = env_path.step(TowerDefenseAction(place_tower=True, row=path_row, col=path_col, tower_type="arrow"))
    test(
        "Cannot place a tower on a path cell",
        (obs_on_path.reward is not None and obs_on_path.reward <= 0),
    )

    env_legal = TowerDefenseEnvironment(difficulty="medium")
    obs_legal = env_legal.reset()
    legal_cells = {tuple(cell) for cell in obs_legal.legal_cells}
    path_cells = {
        divmod(index, env_legal.cfg["grid_size"])
        for index, cell in enumerate(obs_legal.grid)
        if cell == 1
    }
    test("Legal cells exclude path cells", legal_cells.isdisjoint(path_cells))

    # ---------------------------------------------------------------- #
    # 4. Grading logic                                                  #
    # ---------------------------------------------------------------- #
    print("\n── 4. Grading logic (reward system) ────────────────────────")

    env = TowerDefenseEnvironment(difficulty="easy")
    env.reset()

    # Place a tower and run a wave
    action = TowerDefenseAction(place_tower=True, row=1, col=2, tower_type="arrow")
    obs = env.step(action)

    test("Kill reward is positive (+10 each)", env._grader_kill_reward() == 10.0)
    test("Leak penalty is negative (-5 each)", env._grader_leak_penalty() == -5.0)
    test("Wave clear bonus is positive (+20)", env._grader_wave_clear_bonus() == 20.0)
    test("Win bonus is >= 50", env._grader_win_bonus() >= 50.0)

    # grade_episode returns required fields
    env2 = TowerDefenseEnvironment(difficulty="easy")
    env2.reset()
    env2.step(TowerDefenseAction(place_tower=False))
    report = env2.grade_episode()

    for field in ["episode_id", "difficulty", "total_reward", "kills", "leaks",
                  "kill_rate", "base_hp_remaining", "towers_placed", "waves_completed", "score", "game_won"]:
        test(f"grade_episode() has '{field}' field", field in report)

    test("Score is 0-100", 0 <= report["score"] <= 100)
    test("grade_episode difficulty matches env difficulty", report["difficulty"] == "easy")
    test("grade_episode total_waves matches config", report["total_waves"] == env2.cfg["total_waves"])
    test("waves_completed stays within total_waves", 0 <= report["waves_completed"] <= report["total_waves"])
    test("state.game_won matches grader output", env2.state.game_won == report["game_won"])

    # Done episodes should remain stable if stepped again
    env_done = TowerDefenseEnvironment(difficulty="easy")
    env_done.reset()
    env_done._episode_done = True
    env_done._game_won = True
    env_done._game_lost = False
    env_done._waves_completed = env_done.cfg["total_waves"]
    env_done._current_wave = env_done.cfg["total_waves"]
    final_obs = env_done.step(TowerDefenseAction(place_tower=False))
    final_report = env_done.grade_episode()
    test("Done episode stays done on extra step", final_obs.done)
    test("Completed episode reports all waves finished", final_report["waves_completed"] == final_report["total_waves"])
    test("Completed episode keeps state and grader in sync", env_done.state.game_won == final_report["game_won"])

    env_lost = TowerDefenseEnvironment(difficulty="easy")
    env_lost.reset()
    env_lost._episode_done = True
    env_lost._game_won = False
    env_lost._game_lost = True
    env_lost._base_hp = 0
    loss_obs = env_lost.step(TowerDefenseAction(place_tower=False))
    loss_report = env_lost.grade_episode()
    test("Lost episode stays done on extra step", loss_obs.done)
    test("Lost episode keeps state and grader in sync", env_lost.state.game_won == loss_report["game_won"] and env_lost.state.game_lost)

    # ---------------------------------------------------------------- #
    # Summary                                                           #
    # ---------------------------------------------------------------- #
    total = len(results)
    passed = sum(results)
    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{total} tests passed", end="")
    if passed == total:
        print("  🎉  ALL PASS")
    else:
        print(f"  ⚠️   {total - passed} FAILED")
    print("=" * 60 + "\n")

    return passed == total


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
