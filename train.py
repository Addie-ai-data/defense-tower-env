import sys
sys.path.insert(0, "./src")

from stable_baselines3 import PPO # type: ignore
from stable_baselines3.common.env_util import make_vec_env # type: ignore
from gym_env import TowerDefenseGymEnv
import matplotlib.pyplot as plt

# Train on easy for demo
env = TowerDefenseGymEnv(difficulty="easy")

model = PPO("MlpPolicy", env, verbose=1, learning_rate=0.0003, n_steps=2048, batch_size=64, n_epochs=10, gamma=0.99)

# Train for a short time
model.learn(total_timesteps=10000)

# Save model
model.save("ppo_tower_defense")

# Plot rewards (simplified)
# In real, log rewards
print("Training complete. Model saved as ppo_tower_defense.zip")

# To evaluate
obs, _ = env.reset()
total_reward = 0
for _ in range(100):
    action, _ = model.predict(obs)
    obs, reward, done, _, _ = env.step(action)
    total_reward += reward
    if done:
        break
print(f"Trained agent total reward: {total_reward}")