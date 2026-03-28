import gym
import numpy as np
from envs.tower_defense.client import TowerDefenseEnv
from envs.tower_defense.models import TowerDefenseAction

class TowerDefenseGymEnv(gym.Env):
    def __init__(self, difficulty="easy", base_url="http://localhost:8000"):
        super().__init__()
        self.env = TowerDefenseEnv(base_url=base_url)
        self.difficulty = difficulty

        # Define action and observation spaces
        # Actions: place_tower (0/1), row (0-3 for easy), col (0-3), tower_type (0=arrow,1=cannon,2=magic)
        self.action_space = gym.spaces.MultiDiscrete([2, 4, 4, 3])  # Adjust for difficulty

        # Observation: grid (flattened), base_hp, gold, legal_cells (flattened), wave
        # Simplify: flatten grid, base_hp, gold, len(legal_cells)
        grid_size = 16 if difficulty == "easy" else 36 if difficulty == "medium" else 64
        self.observation_space = gym.spaces.Box(low=0, high=4, shape=(grid_size + 3,), dtype=np.float32)

    def reset(self):
        obs = self.env.reset(difficulty=self.difficulty)
        return self._obs_to_array(obs), {}

    def step(self, action):
        place, row, col, tower_type = action
        tower_types = ["arrow", "cannon", "magic"]
        act = TowerDefenseAction(
            place_tower=bool(place),
            row=int(row),
            col=int(col),
            tower_type=tower_types[int(tower_type)]
        )
        obs = self.env.step(act)
        reward = obs.reward or 0
        done = obs.done
        return self._obs_to_array(obs), reward, done, False, {}

    def _obs_to_array(self, obs):
        grid_flat = np.array(obs.grid, dtype=np.float32)
        return np.concatenate([grid_flat, [obs.base_hp, obs.gold, len(obs.legal_cells)]])

    def render(self, mode='human'):
        pass